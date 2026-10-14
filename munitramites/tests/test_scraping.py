"""Pruebas del comando de scraping (con el HTTP simulado, sin red)."""

import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from munitramites.models import Municipio, Organismo, Requisito, Tema, Tramite

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
            'munitramites.management.commands.scrapear_sitios._traer',
            side_effect=_fake_traer,
        ):
            call_command(
                'scrapear_sitios', csv=self.ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

    def test_importa_los_organismos_de_la_planilla(self):
        with patch(
            'munitramites.management.commands.scrapear_sitios._traer',
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
        self.assertEqual(dni.enlace_oficial,
                         'https://ejemplo.gob.ar/dni/renovacion')
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
        # La URL trae «turno»: queda cargada como enlace de turnos.
        self.assertEqual(
            licencia.enlace_turnos,
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
            'munitramites.management.commands.scrapear_sitios._traer',
            side_effect=lambda url: paginas.get(url),
        ):
            call_command(
                'scrapear_sitios', csv=ruta, espera=0,
                stdout=StringIO(), stderr=StringIO(),
            )

        self.assertEqual(Tramite.objects.count(), 1)
        self.assertEqual(
            Tramite.objects.get().enlace_oficial,
            'https://ejemplo.gob.ar/dni/corto',
        )

    def test_un_sitio_caido_no_tumba_el_comando(self):
        ruta = _csv(
            'NOMBRE,OCUPACION,LINK_SITIO_OFICIAL\n'
            'Sitio Caído,Prueba,https://caido.gob.ar/\n'
        )
        self.addCleanup(os.unlink, ruta)

        with patch(
            'munitramites.management.commands.scrapear_sitios._traer',
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
            'munitramites.management.commands.scrapear_sitios._traer',
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
            'munitramites.management.commands.scrapear_sitios._traer',
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
