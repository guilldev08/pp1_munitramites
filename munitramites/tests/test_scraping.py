"""Pruebas del scraper (con el HTTP simulado, sin red).

La lógica vive en munitramites/services/scraper/; acá se prueba el
command completo (que es una cáscara fina) y el criterio de relevancia
que decide qué link es un trámite y qué página es una ficha.
"""

import os
import tempfile
from io import StringIO
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.core.management import call_command

from munitramites.models import Municipio, Organismo, Requisito, Tema, Tramite
from munitramites.services.scraper.busqueda import relevancia
from munitramites.services.scraper.fichas import extraccion

from .base import TestCase

HTML_INICIO = """
<html><body>
  <a href="/noticias/sumate">Noticias de la comunidad</a>
  <a href="/institucional">Institucional</a>
  <a href="/dni/renovacion">Renovación del DNI en línea</a>
  <a href="/turnos/licencia-conducir">Licencia de conducir - turnos</a>
</body></html>
"""

HTML_DNI = """
<html><head>
  <meta name="description"
        content="Trámite de renovación del DNI para los vecinos de la provincia.">
</head><body>
  <h1>Renovación del DNI</h1>
  <h2>Requisitos</h2>
  <ul>
    <li>DNI anterior en vigor</li>
    <li>Partida de nacimiento</li>
    <li>Comprobante de domicilio</li>
  </ul>
</body></html>
"""

HTML_LICENCIA = """
<html><body>
  <h1>Licencia de conducir</h1>
  <p>El trámite de licencia de conducir se realiza con turno previo en la
  Dirección de Tránsito de la provincia de Misiones.</p>
</body></html>
"""

PAGINAS = {
    'https://ejemplo.gob.ar/': HTML_INICIO,
    'https://ejemplo.gob.ar/dni/renovacion': HTML_DNI,
    'https://ejemplo.gob.ar/turnos/licencia-conducir': HTML_LICENCIA,
}


def _fake_traer(url):
    return PAGINAS.get(url)


def _csv(texto):
    archivo = tempfile.NamedTemporaryFile(
        'w', suffix='.csv', delete=False, encoding='utf-8',
    )
    archivo.write(texto)
    archivo.close()
    return archivo.name


class ScrapingTests(TestCase):
    """scrapear_sitios: importa la planilla y crea trámites inactivos."""

    def setUp(self):
        self.ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Ejemplo de Misiones,Prueba de scraping,https://ejemplo.gob.ar/\n'
        )
        self.addCleanup(os.unlink, self.ruta)

    def _correr(self):
        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=_fake_traer,
        ):
            call_command(
                'scrapear_sitios', csv=self.ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

    def test_importa_los_organismos_de_la_planilla(self):
        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
        ):
            call_command(
                'scrapear_sitios', csv=self.ruta, solo_organismos=True,
                stdout=StringIO(),
            )

        organismo = Organismo.objects.get(nombre='Ejemplo de Misiones')
        self.assertEqual(organismo.sitio, 'https://ejemplo.gob.ar/')
        self.assertEqual(organismo.ocupacion, 'Prueba de scraping')
        self.assertEqual(Tramite.objects.count(), 0)

    def test_crea_tramites_inactivos_con_requisitos(self):
        self._correr()

        dni = Tramite.objects.get(titulo='Renovación del DNI en línea')
        # Inactivo: nada del scraping se publica sin revisión.
        self.assertFalse(dni.activo)
        self.assertEqual(
            dni.enlaces.get(nombre='Sitio del organismo').url,
            'https://ejemplo.gob.ar/dni/renovacion',
        )
        self.assertEqual(dni.descripcion,
                         'Trámite de renovación del DNI para los vecinos '
                         'de la provincia.')
        self.assertEqual(dni.tema.nombre, 'Documentación')
        self.assertEqual(dni.modalidad, 'virtual')
        self.assertEqual(dni.municipio.nombre, 'Posadas')

        requisitos = list(
            dni.requisitos.order_by('orden').values_list(
                'descripcion', 'orden'
            )
        )
        self.assertEqual(requisitos, [
            ('DNI anterior en vigor', 1),
            ('Partida de nacimiento', 2),
            ('Comprobante de domicilio', 3),
        ])

    def test_los_links_de_noticias_no_se_toman_y_turnos_se_marca(self):
        self._correr()

        self.assertEqual(Tramite.objects.count(), 2)
        self.assertFalse(
            Tramite.objects.filter(titulo__icontains='Noticias').exists()
        )

        licencia = Tramite.objects.get(
            titulo='Licencia de conducir - turnos'
        )
        self.assertEqual(licencia.tema.nombre, 'Tránsito')
        self.assertEqual(licencia.modalidad, 'presencial')
        # La URL trae «turno»: queda cargada como botón de turnos.
        self.assertEqual(
            licencia.enlaces.get(nombre='Pedir turno').url,
            'https://ejemplo.gob.ar/turnos/licencia-conducir',
        )
        # Sin sección de requisitos ni <li> con pinta de requerimiento.
        self.assertEqual(licencia.requisitos.count(), 0)

    def test_correr_dos_veces_no_duplica(self):
        self._correr()
        self._correr()

        self.assertEqual(Tramite.objects.count(), 2)

    def test_las_urls_largas_se_descartan_en_vez_de_reventar(self):
        """Firebird corta en seco en 200/300: mejor no cargarlas."""
        largo = 'https://ejemplo.gob.ar/gestion/' + 'x' * 300
        html = (
            '<html><body>'
            f'<a href="{largo}">Trámite con URL larguísima</a>'
            '<a href="/dni/corto">Solicitud de DNI</a>'
            '</body></html>'
        )
        paginas = {
            'https://ejemplo.gob.ar/': html,
            'https://ejemplo.gob.ar/dni/corto': HTML_DNI,
        }
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Ejemplo de Misiones,Prueba,https://ejemplo.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=lambda url: paginas.get(url),
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

        self.assertEqual(Tramite.objects.count(), 1)
        tramite = Tramite.objects.get()
        self.assertEqual(
            tramite.enlaces.get(nombre='Sitio del organismo').url,
            'https://ejemplo.gob.ar/dni/corto',
        )

    def test_un_sitio_caido_no_tumba_el_comando(self):
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Sitio Caído,Prueba,https://caido.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            return_value=None,
        ):
            salida = StringIO()
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=salida, stderr=salida,
            )

        self.assertIn('no se pudo leer', salida.getvalue())
        self.assertIn('1 sitio(s) no contestaron.', salida.getvalue())
        self.assertEqual(Tramite.objects.count(), 0)

    def test_el_municipio_de_una_municipalidad_se_infiere(self):
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Municipalidad de Oberá,Gobierno municipal,'
            'https://ejemplo.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=_fake_traer,
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

        # Sin acentos, como los carga el seed.
        self.assertTrue(Municipio.objects.filter(nombre='Obera').exists())
        tramite = Tramite.objects.filter(activo=False).first()
        self.assertEqual(tramite.municipio.nombre, 'Obera')

    def test_el_tema_se_elige_segun_el_organismo(self):
        self._correr()

        self.assertEqual(
            Tema.objects.get(nombre='Documentación').tramites.count(), 1
        )
        self.assertEqual(
            Tema.objects.get(nombre='Tránsito').tramites.count(), 1
        )

    def test_segue_las_puertas_del_portal(self):
        """Si los trámites viven detrás de «Servicios», se entra y se buscan."""
        html_inicio = (
            '<html><body>'
            '<a href="/servicios/">Servicios al ciudadano</a>'
            '</body></html>'
        )
        html_servicios = (
            '<html><body>'
            '<a href="/certificado-antecedentes">'
            'Certificado de antecedentes penales</a>'
            '</body></html>'
        )
        html_ficha = (
            '<html><body><h1>Antecedentes</h1>'
            '<h2>Requisitos</h2><ul>'
            '<li>DNI original y fotocopia</li></ul></body></html>'
        )
        paginas = {
            'https://portal.gob.ar/': html_inicio,
            'https://portal.gob.ar/servicios/': html_servicios,
            'https://portal.gob.ar/certificado-antecedentes': html_ficha,
        }
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Portal de Prueba,Prueba,https://portal.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=lambda url: paginas.get(url),
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

        tramite = Tramite.objects.get(
            titulo='Certificado de antecedentes penales'
        )
        self.assertFalse(tramite.activo)
        self.assertEqual(tramite.requisitos.count(), 1)


class RelevanciaTests(TestCase):
    """El criterio que arregla el «tomaba cualquier cosa»."""

    def test_una_palabra_debil_sola_no_alcanza(self):
        # «Impuestos» o «Registro» sueltos no son un trámite.
        self.assertLess(
            relevancia.puntaje_link('Impuestos', '/impuestos'),
            relevancia.PUNTAJE_MINIMO,
        )
        self.assertLess(
            relevancia.puntaje_link('Registro', '/registro'),
            relevancia.PUNTAJE_MINIMO,
        )

    def test_una_palabra_fuerte_alcanza(self):
        self.assertGreaterEqual(
            relevancia.puntaje_link('Partida de nacimiento', '/partida'),
            relevancia.PUNTAJE_MINIMO,
        )
        self.assertGreaterEqual(
            relevancia.puntaje_link('Licencia de conducir', '/licencia'),
            relevancia.PUNTAJE_MINIMO,
        )

    def test_un_link_de_menu_vale_la_mitad(self):
        self.assertLess(
            relevancia.puntaje_link('Trámites', '/tramites/', en_menu=True),
            relevancia.PUNTAJE_MINIMO,
        )

    def test_las_noticias_y_los_pdfs_son_ruido(self):
        self.assertTrue(relevancia.es_ruido('/noticias/sumate'))
        self.assertTrue(relevancia.es_ruido('/transparencia/boletin.pdf'))
        # Los botones de «compartir» de los sitios no son puertas.
        self.assertTrue(relevancia.es_ruido(
            'https://www.addtoany.com/add_to/x?linkurl=https%3A%2F%2Fmisiones'
        ))
        self.assertFalse(relevancia.es_ruido('/dni/renovacion'))

    def test_un_indice_de_seccion_no_parece_ficha(self):
        indice = BeautifulSoup(
            '<html><body><h1>Trámites</h1>'
            '<a href="/dni">Renovación del DNI</a>'
            '<a href="/pasaporte">Pasaporte</a>'
            '<a href="/licencia">Licencia de conducir</a>'
            '<a href="/partida">Partida de nacimiento</a>'
            '<a href="/antecedentes">Antecedentes penales</a>'
            '</body></html>',
            'html.parser',
        )
        self.assertFalse(extraccion.parece_ficha(indice))

    def test_una_ficha_con_requisitos_parece_ficha(self):
        self.assertTrue(extraccion.parece_ficha(
            BeautifulSoup(HTML_DNI, 'html.parser')
        ))

    def test_un_menu_suelto_no_produce_tramites(self):
        """Una home que es solo un menú no carga trámites de relleno."""
        html = (
            '<html><body><nav>'
            '<a href="/inicio">Inicio</a>'
            '<a href="/servicios">Servicios</a>'
            '<a href="/contacto">Contacto</a>'
            '<a href="/transparencia">Transparencia</a>'
            '</nav></body></html>'
        )
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Ejemplo de Misiones,Prueba,https://ejemplo.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=lambda url: (
                html if url == 'https://ejemplo.gob.ar/' else None
            ),
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

        self.assertEqual(Tramite.objects.count(), 0)


class _ScraperTestCase(TestCase):
    """Corre el comando con el HTTP simulado por un mapa de páginas."""

    def correr(self, paginas, filas):
        ruta = _csv('NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n' + filas)
        self.addCleanup(os.unlink, ruta)
        with patch(
            'munitramites.services.scraper.busqueda.rastreo.traer',
            side_effect=lambda url: paginas.get(url),
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )


FICHA_DNI = (
    '<html><body><h1>Renovación del DNI</h1>'
    '<p>El trámite de renovación del DNI se hace en el Registro Civil de '
    'la provincia, con la documentación a mano.</p>'
    '</body></html>'
)


class ExtraccionTests(_ScraperTestCase):
    """Los datos salen del contenido de la ficha, no del menú del portal."""

    def test_el_titulo_sale_de_la_pagina_y_no_del_menu(self):
        """El link arrastra el menú: «Inmobiliario Trámites y Gestiones…»."""
        paginas = {
            'https://atm.gob.ar/': (
                '<html><body><a href="/inmobiliario">'
                'Inmobiliario Trámites y Gestiones Información General'
                '</a></body></html>'
            ),
            'https://atm.gob.ar/inmobiliario': (
                '<html><head><title>Inmobiliario - ATM</title></head><body>'
                '<h1>Trámites y Gestiones</h1>'
                '<p>Pasos a seguir para la emisión de la Boleta de Impuesto '
                'Inmobiliario, con los datos de la partida.</p>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'Agencia Tributaria,Impuestos,https://atm.gob.ar/\n')

        self.assertEqual(Tramite.objects.get().titulo, 'Inmobiliario')

    def test_los_requisitos_salen_de_la_lista_de_requisitos(self):
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/dni">Trámite de DNI</a></body></html>'
            ),
            'https://x.gob.ar/dni': (
                '<html><body><h1>Renovación del DNI</h1>'
                '<p>El trámite de renovación del DNI se hace en el Registro '
                'Civil de la provincia, con la documentación a mano.</p>'
                '<nav><ul>'
                '<li>Galería de fotos</li><li>Multimedia</li>'
                '<li>Turno online</li>'
                '</ul></nav>'
                '<h2>Requisitos</h2>'
                '<ul>'
                '<li>DNI anterior en vigor</li>'
                '<li>DNI anterior en vigor</li>'
                '<li>Comprobante de domicilio</li>'
                '</ul>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'Registro Civil,Documentacion,https://x.gob.ar/\n')

        requisitos = list(
            Tramite.objects.get().requisitos.values_list('descripcion', flat=True)
        )
        # Ni menú colado, ni el mismo requisito dos veces.
        self.assertEqual(
            requisitos, ['DNI anterior en vigor', 'Comprobante de domicilio'],
        )

    def test_sin_encabezado_no_se_toma_cualquier_lista(self):
        """El respaldo viejo colaba «Galería de fotos» por la palabra «foto»."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/cud">Beneficios para Personas con CUD</a>'
                '</body></html>'
            ),
            'https://x.gob.ar/cud': (
                '<html><body><h1>Beneficios para Personas con CUD</h1>'
                '<p>El organismo otorga un subsidio para el trámite de las '
                'personas con CUD en toda la provincia.</p>'
                '<ul><li>Galería de fotos</li><li>Galería de videos</li>'
                '<li>Turno online</li></ul>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'IPRODHA,Vivienda,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.get().requisitos.count(), 0)

    def test_la_descripcion_no_es_la_bajada_del_sitio(self):
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/becas">Becas de Albergues</a></body></html>'
            ),
            'https://x.gob.ar/becas': (
                '<html><head><meta name="description" content="Sitio de la '
                'Universidad Nacional - Argentina - Año 2026"></head><body>'
                '<h1>Becas de Albergues</h1>'
                '<p>Pagina Oficial del registro civil de la provincia de '
                'Misiones.</p>'
                '<p>La universidad cubre el alojamiento de los estudiantes '
                'que hacen el trámite de la beca y viven lejos de la sede '
                'central.</p>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'UNAM,Educacion,https://x.gob.ar/\n')

        self.assertIn('cubre el alojamiento', Tramite.objects.get().descripcion)

    def test_una_pagina_sin_datos_propios_no_se_carga(self):
        """Menciona «trámite» pero no trae descripción ni requisitos."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/agua-nuevo-equipamiento">Becas: '
                'nuevo equipamiento</a></body></html>'
            ),
            'https://x.gob.ar/agua-nuevo-equipamiento': (
                '<html><body><h1>Becas: nuevo equipamiento</h1>'
                '<p>El trámite de la beca sigue vigente.</p>'
                '<p>Sitio de la Universidad Nacional - Argentina - Año '
                '2026. Todos los derechos reservados.</p>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'UNAM,Educacion,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.count(), 0)

    def test_el_enlace_de_turnos_sale_de_la_ficha(self):
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/licencia">Licencia de conducir</a>'
                '</body></html>'
            ),
            'https://x.gob.ar/licencia': (
                '<html><body><h1>Licencia de conducir</h1>'
                '<p>El trámite de licencia de conducir se realiza con turno '
                'previo en la Dirección de Tránsito de la provincia.</p>'
                '<a href="https://turnos.gob.ar/licencia">Turno online</a>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'Direccion de Transito,Transito,https://x.gob.ar/\n')

        tramite = Tramite.objects.get()
        self.assertEqual(
            tramite.enlaces.get(nombre='Pedir turno').url,
            'https://turnos.gob.ar/licencia',
        )
        self.assertEqual(
            tramite.enlaces.get(nombre='Sitio del organismo').url,
            'https://x.gob.ar/licencia',
        )

    def test_una_noticia_no_se_sigue_por_su_slug(self):
        """Un slug de titular («…-nuevo-equipamiento-…») es una noticia."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/becas-nuevo-equipamiento-para-el-'
                'servicio-de-agua-en-garupa">Becas: nuevo equipamiento para '
                'el servicio de agua en Garupá</a></body></html>'
            ),
            'https://x.gob.ar/becas-nuevo-equipamiento-para-el-servicio-de-'
            'agua-en-garupa': FICHA_DNI,
        }
        self.correr(paginas, 'SAMSA,Agua,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.count(), 0)

    def test_un_listado_de_tema_no_es_un_tramite(self):
        """`/tema/…` es un listado de servicios, no la ficha de uno."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/tema/becas">Becas y servicios '
                'educativos</a></body></html>'
            ),
            'https://x.gob.ar/tema/becas': FICHA_DNI,
        }
        self.correr(paginas, 'Argentina.gob.ar,Educacion,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.count(), 0)

    def test_un_menu_de_links_no_es_una_lista_de_requisitos(self):
        """Una lista de links con palabras de requisito sigue siendo menú."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/licencia">Licencia de conducir</a>'
                '</body></html>'
            ),
            'https://x.gob.ar/licencia': (
                '<html><body><h1>Licencia de conducir</h1>'
                '<p>El trámite de licencia de conducir se realiza con turno '
                'previo en la Dirección de Tránsito de la provincia.</p>'
                '<ul>'
                '<li><a href="/guia-dni">DNI, Nuevo Ejemplar, Denuncia</a></li>'
                '<li><a href="/guia-apto">Formulario de Apto Médico</a></li>'
                '<li><a href="/guia-copia">Fotocopia de DNI y certificado</a>'
                '</li>'
                '</ul>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'Direccion de Transito,Transito,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.get().requisitos.count(), 0)

    def test_una_lista_de_descargas_no_es_una_descripcion(self):
        """Un párrafo con links es una lista de descargas, no prosa."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/saneamiento">Habilitación de '
                'saneamiento básico</a></body></html>'
            ),
            'https://x.gob.ar/saneamiento': (
                '<html><body><h1>Habilitación de saneamiento básico</h1>'
                '<h2>Trámites y descargas del departamento de saneamiento '
                'básico de la provincia</h2>'
                '<p><a href="/guia.pdf">Guía de trámites</a> '
                '<a href="/formulario.pdf">Formulario de inscripción</a> '
                '<a href="/planilla.pdf">Planilla de solicitud</a></p>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'Salud Publica,Salud,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.count(), 0)

    def test_el_title_escueto_deja_pasar_al_link(self):
        """«INSSJP» en el <title> dice menos que «Rehabilitación para…»."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/rehabilitacion">Rehabilitación para '
                'personas con discapacidad</a></body></html>'
            ),
            'https://x.gob.ar/rehabilitacion': (
                '<html><head><title>INSSJP</title></head><body>'
                '<p>El trámite de rehabilitación acompaña a las personas con '
                'discapacidad en la recuperación de sus aptitudes.</p>'
                '</body></html>'
            ),
        }
        self.correr(paginas, 'PAMI,Salud,https://x.gob.ar/\n')

        self.assertEqual(
            Tramite.objects.get().titulo,
            'Rehabilitación para personas con discapacidad',
        )

    def test_el_rastreo_entra_dos_veces_hasta_la_ficha(self):
        """Las fichas están a dos o tres clicks: home → Trámites → Servicios."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body><a href="/tramites">Trámites</a></body></html>'
            ),
            'https://x.gob.ar/tramites': (
                '<html><body><a href="/servicios">Servicios</a></body></html>'
            ),
            'https://x.gob.ar/servicios': (
                '<html><body><a href="/dni">Renovación del DNI</a></body></html>'
            ),
            'https://x.gob.ar/dni': FICHA_DNI,
        }
        self.correr(paginas, 'Registro Civil,Documentacion,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.get().titulo, 'Renovación del DNI')


class SinRedundanciaTests(_ScraperTestCase):
    """La misma ficha, o el mismo trámite, no se cargan dos veces."""

    def test_la_misma_ficha_con_otra_url_no_se_duplica(self):
        """`/dni/`, `http://www…` y `/dni` son la misma página."""
        paginas = {
            'https://x.gob.ar/': (
                '<html><body>'
                '<a href="/dni/">Renovación del DNI</a>'
                '<a href="https://www.x.gob.ar/dni">Renovación del DNI</a>'
                '</body></html>'
            ),
            'https://x.gob.ar/dni/': FICHA_DNI,
            'https://www.x.gob.ar/dni': FICHA_DNI,
        }
        self.correr(paginas, 'Registro Civil,Documentacion,https://x.gob.ar/\n')

        self.assertEqual(Tramite.objects.count(), 1)

    def test_el_mismo_tramite_en_dos_organismos_no_se_duplica(self):
        paginas = {
            'https://a.gob.ar/': (
                '<html><body><a href="/dni">Trámite de DNI</a></body></html>'
            ),
            'https://b.gob.ar/': (
                '<html><body><a href="/dni">Trámite de DNI</a></body></html>'
            ),
            'https://a.gob.ar/dni': FICHA_DNI,
            'https://b.gob.ar/dni': FICHA_DNI,
        }
        self.correr(
            paginas,
            'Organismo A,Documentacion,https://a.gob.ar/\n'
            'Organismo B,Documentacion,https://b.gob.ar/\n',
        )

        self.assertEqual(Tramite.objects.count(), 1)
