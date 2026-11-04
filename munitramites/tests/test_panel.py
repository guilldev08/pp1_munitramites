"""ESP-02 / RF-07, RF-10, RF-11, RF-13 — El panel propio (/panel/).

Matriz de aceptación del panel de administración:

* **Acceso**: sin sesión al login, ciudadano a la portada con mensaje
  claro, administrador y superusuario adentro.
* **Centro de Trámites**: alta con requisitos y enlaces, edición,
  publicar / desactivar / destacar.
* **Centro de Consultas**: ver todas y responder (RF-10).
* **Usuarios**: crear cuentas y cambiar roles SIN poder crear, editar ni
  eliminar superusuarios, ni elevar a nadie (RF-11 / RF-13).
* **Temas**: alta desde el panel (RF-07).
"""

import tempfile
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from munitramites.models import (
    ArchivoTramite, Consulta, Direccion, Perfil, Requisito, Tema, Ticket,
    Tramite,
)

from .base import (
    TestCase, administrador, administrativo, ciudadano, municipio,
    organismo, superusuario, tramite,
)

# URLs del panel, para barrer el acceso en un solo test
URLS_PANEL = (
    'panel', 'panel_tramites', 'panel_tramite_nuevo', 'panel_consultas',
    'panel_tickets', 'panel_usuarios', 'panel_usuario_nuevo', 'panel_temas',
)


class AccesoTests(TestCase):
    """¿Quién entra al panel y con qué mensaje si no corresponde?"""

    def test_sin_sesion_lo_manda_al_login(self):
        for nombre in URLS_PANEL:
            r = self.client.get(reverse(nombre))

            self.assertEqual(r.status_code, 302, nombre)
            self.assertIn(reverse('login'), r['Location'], nombre)

    def test_al_ciudadano_lo_manda_a_la_portada_con_mensaje(self):
        self.client.force_login(ciudadano(username='ana'))

        for nombre in URLS_PANEL:
            r = self.client.get(reverse(nombre))

            self.assertEqual(r.status_code, 302, nombre)
            self.assertEqual(r['Location'], reverse('inicio'), nombre)

        r = self.client.get(reverse('panel'), follow=True)
        self.assertContains(r, 'solo para administradores')

    def test_al_administrador_le_todas_las_secciones(self):
        self.client.force_login(administrador())

        for nombre in URLS_PANEL:
            self.assertEqual(
                self.client.get(reverse(nombre)).status_code, 200, nombre
            )

    def test_al_administrativo_le_faltan_solo_las_cuentas(self):
        self.client.force_login(administrativo())

        for nombre in ('panel', 'panel_tramites', 'panel_tramite_nuevo',
                       'panel_consultas', 'panel_temas'):
            self.assertEqual(
                self.client.get(reverse(nombre)).status_code, 200, nombre
            )

        for nombre in ('panel_usuarios', 'panel_usuario_nuevo'):
            r = self.client.get(reverse(nombre))

            self.assertEqual(r.status_code, 302, nombre)
            self.assertEqual(r['Location'], reverse('panel'), nombre)

    def test_al_superusuario_tambien(self):
        self.client.force_login(superusuario())

        r = self.client.get(reverse('panel'))

        self.assertEqual(r.status_code, 200)
        # Ni siquiera él: el /admin/ no tiene botón, solo enlace directo
        self.assertNotContains(r, 'Django admin')

    def test_las_urls_de_detalle_tambien_estan_cerradas(self):
        t = tramite()
        c = Consulta.objects.create(asunto='Hola', contenido='¿Abren?')
        ticket = Ticket.objects.create(asunto='Ticket', descripcion='...')
        self.client.force_login(ciudadano(username='ana'))

        for url in (reverse('panel_tramite_editar', args=[t.pk]),
                    reverse('panel_tramite_estado', args=[t.pk]),
                    reverse('panel_consulta', args=[c.pk]),
                    reverse('panel_ticket_detalle', args=[ticket.pk]),
                    reverse('panel_ticket_eliminar', args=[ticket.pk]),
                    reverse('panel_usuario_editar', args=[1]),
                    reverse('panel_usuario_eliminar', args=[1])):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('inicio'), url)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CentroDeTramitesTests(TestCase):
    """CRUD del catálogo: alta, edición y publicación (RF-07)."""

    def setUp(self):
        self.admin = administrador()
        self.client.force_login(self.admin)

    def test_el_listado_muestra_los_activos_y_los_inactivos(self):
        tramite()
        tramite(titulo='Trámite dado de baja', activo=False)

        r = self.client.get(reverse('panel_tramites'))

        self.assertContains(r, 'Renovacion de DNI')
        self.assertContains(r, 'Trámite dado de baja')

    def test_el_filtro_por_estado_anda(self):
        tramite()
        tramite(titulo='Trámite dado de baja', activo=False)

        r = self.client.get(reverse('panel_tramites') + '?estado=inactivos')

        self.assertNotContains(r, 'Renovacion de DNI')
        self.assertContains(r, 'Trámite dado de baja')

    def test_el_buscador_filtra_por_titulo_y_por_organismo(self):
        tramite()
        tramite(titulo='Libreta de conducir')

        r = self.client.get(reverse('panel_tramites') + '?q=conducir')

        self.assertContains(r, 'Libreta de conducir')
        self.assertNotContains(r, 'Renovacion de DNI')

    def test_el_filtro_lateral_por_tema_anda(self):
        t = tramite()
        tramite(titulo='Inscripcion escolar', tema='Educacion')

        r = self.client.get(reverse('panel_tramites') + f'?tema={t.tema.pk}')

        self.assertContains(r, 'Renovacion de DNI')
        self.assertNotContains(r, 'Inscripcion escolar')

    def test_las_columnas_se_pueden_ordenar(self):
        tramite()
        tramite(titulo='AAA al principio')

        r = self.client.get(reverse('panel_tramites') + '?orden=titulo')

        titulos = [t.titulo for t in r.context['pagina'].object_list]
        self.assertEqual(titulos, sorted(titulos))

    def test_las_acciones_masivas_actuan_sobre_lo_marcado(self):
        t1 = tramite(activo=False)
        t2 = tramite(titulo='Otro trámite', activo=False)

        r = self.client.post(reverse('panel_tramites_accion'), {
            'seleccion': [str(t1.pk)], 'accion': 'activar',
            'siguiente': reverse('panel_tramites'),
        })

        self.assertRedirects(r, reverse('panel_tramites'))
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertTrue(t1.activo)
        self.assertFalse(t2.activo)

    def test_sin_seleccion_no_anda_nada_y_avisa(self):
        tramite(activo=False)

        r = self.client.post(reverse('panel_tramites_accion'), {
            'accion': 'activar', 'siguiente': reverse('panel_tramites'),
        }, follow=True)

        self.assertContains(r, 'Elegí una acción y marcá al menos un trámite')
        self.assertFalse(Tramite.objects.filter(activo=True).exists())

    def test_el_boton_de_fila_actua_sobre_un_solo_tramite(self):
        t1 = tramite(activo=False)
        t2 = tramite(titulo='Otro trámite', activo=False)

        self.client.post(reverse('panel_tramites_accion'), {
            f'fila_{t1.pk}': 'activar',
            'siguiente': reverse('panel_tramites'),
        })

        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertTrue(t1.activo)
        self.assertFalse(t2.activo)

    def test_desde_el_form_se_crea_un_organismo_nuevo(self):
        """No hace falta irse del CRUD a cargar el organismo: se crea ahí."""
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Registro de Bicicletas',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': '',
            'organismo_nuevo': 'Direccion de Licencias de Trafico',
            'descripcion': 'Se tramita en el municipio.',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '1', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '1', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Registro de Bicicletas')
        self.assertEqual(
            nuevo.organismo.nombre, 'Direccion de Licencias de Trafico'
        )

    def test_desde_el_form_se_crea_un_municipio_nuevo(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Trámite de Oberá',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipio_nuevo': 'Obera',
            'organismo': organismo().pk,
            'organismo_nuevo': '',
            'descripcion': 'Se tramita en la municipalidad.',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '1', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '1', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Trámite de Oberá')
        self.assertEqual(nuevo.municipio.nombre, 'Obera')

    def test_el_form_trae_filas_de_mas_y_boton_de_agregar(self):
        """Filas vacías listas y un botón que clona más en los tres inlines."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'requisitos-2-descripcion')
        self.assertContains(r, 'enlaces-2-nombre')
        self.assertContains(r, 'direcciones-1-lugar')
        self.assertContains(r, 'data-agregar-fila="requisitos"')
        self.assertContains(r, 'data-agregar-fila="enlaces"')
        self.assertContains(r, 'data-agregar-fila="direcciones"')
        self.assertContains(r, 'requisitos-__prefix__-descripcion')

    def test_los_requisitos_se_numeran_solos_y_la_fila_borrada_sale(self):
        """El número lo pone el panel y la fila «Eliminar» se saca de la lista."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'data-numerar')
        self.assertContains(r, 'Requisitos <span data-numero>1</span>')
        self.assertContains(r, 'data-aviso-borrado="requisito"')
        self.assertContains(r, 'data-aviso-borrado="enlace"')
        self.assertContains(r, 'data-aviso-borrado="dirección"')

    def test_los_enlaces_no_son_campos_fijos(self):
        """Cada enlace se carga como botón con nombre y URL, no hardcodeado."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertNotContains(r, 'Enlace turnos')
        self.assertNotContains(r, 'name="enlace_turnos"')
        self.assertNotContains(r, 'name="enlace_oficial"')
        self.assertContains(r, 'Enlace oficial <span data-numero')
        self.assertContains(r, 'enlaces-0-nombre')
        self.assertContains(r, 'enlaces-0-url')

    def test_crea_un_tramite_con_requisitos_y_enlaces(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Pasaporte argentino',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se tramita con turno previo.',
            'destacado': 'on', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '1', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'requisitos-0-descripcion': 'DNI en vigor y partida de nacimiento',
            'requisitos-0-orden': '1',
            'enlaces-TOTAL_FORMS': '1', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
            'enlaces-0-nombre': 'Pedir turno',
            'enlaces-0-url': 'https://turnos.ejemplo.gob.ar',
            'enlaces-0-orden': '1',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Pasaporte argentino')
        self.assertTrue(nuevo.activo)
        self.assertEqual(nuevo.requisitos.count(), 1)
        self.assertEqual(nuevo.enlaces.count(), 1)
        self.assertEqual(
            nuevo.enlaces.first().url, 'https://turnos.ejemplo.gob.ar'
        )

    def test_crea_un_tramite_con_varias_direcciones(self):
        """Un trámite puede tener sedes en municipios distintos."""
        obera = municipio('Obera')
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Trámite con dos sedes',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se puede hacer en dos municipios.',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
            'direcciones-TOTAL_FORMS': '2', 'direcciones-INITIAL_FORMS': '0',
            'direcciones-MIN_NUM_FORMS': '0',
            'direcciones-MAX_NUM_FORMS': '1000',
            'direcciones-0-lugar': 'Sede Centro',
            'direcciones-0-municipio': municipio().pk,
            'direcciones-0-direccion': 'Av. Mitre 100',
            'direcciones-1-lugar': 'Sede Oberá',
            'direcciones-1-municipio': obera.pk,
            'direcciones-1-direccion': 'Ruta 14 km 2',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Trámite con dos sedes')
        self.assertEqual(nuevo.direcciones.count(), 2)
        self.assertEqual(
            nuevo.direcciones.get(lugar='Sede Oberá').municipio, obera
        )

    def test_el_form_trae_la_seccion_de_archivos(self):
        """El panel permite subir documentos y el form va con multipart."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'enctype="multipart/form-data"')
        self.assertContains(r, 'Documentos y formularios')
        self.assertContains(r, 'archivos-0-archivo')
        self.assertContains(r, 'data-agregar-fila="archivos"')
        self.assertContains(r, 'archivos-__prefix__-archivo')

    def test_crea_un_tramite_con_un_archivo_descargable(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Certificado de residencia',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se pide en la municipalidad.',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0',
            'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0',
            'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0',
            'enlaces-MAX_NUM_FORMS': '1000',
            'archivos-TOTAL_FORMS': '1', 'archivos-INITIAL_FORMS': '0',
            'archivos-MIN_NUM_FORMS': '0',
            'archivos-MAX_NUM_FORMS': '1000',
            'archivos-0-titulo': 'Formulario de solicitud',
            'archivos-0-tipo': 'formulario',
            'archivos-0-descripcion': 'Se completa a mano',
            'archivos-0-archivo': SimpleUploadedFile(
                'solicitud.pdf', b'%PDF-1.4 contenido',
                content_type='application/pdf',
            ),
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Certificado de residencia')
        archivo = nuevo.archivos.get()
        self.assertEqual(archivo.titulo, 'Formulario de solicitud')
        self.assertEqual(archivo.tipo, ArchivoTramite.Tipo.FORMULARIO)
        self.assertEqual(archivo.orden, 0)
        self.assertTrue(archivo.archivo.name.endswith('.pdf'))

    def test_edita_y_borra_un_archivo(self):
        t = tramite()
        a = ArchivoTramite.objects.create(
            tramite=t, titulo='Instructivo viejo', orden=0,
            archivo=SimpleUploadedFile('viejo.pdf', b'%PDF-1.4'),
        )

        r = self.client.post(
            reverse('panel_tramite_editar', args=[t.pk]), {
                'titulo': t.titulo, 'tema': t.tema.pk,
                'modalidad': t.modalidad, 'municipios': [t.municipio.pk],
                'organismo': t.organismo.pk, 'descripcion': t.descripcion,
                'destacado': '', 'activo': 'on',
                'requisitos-TOTAL_FORMS': '0',
                'requisitos-INITIAL_FORMS': '0',
                'requisitos-MIN_NUM_FORMS': '0',
                'requisitos-MAX_NUM_FORMS': '1000',
                'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
                'enlaces-MIN_NUM_FORMS': '0',
                'enlaces-MAX_NUM_FORMS': '1000',
                'archivos-TOTAL_FORMS': '1',
                'archivos-INITIAL_FORMS': '1',
                'archivos-MIN_NUM_FORMS': '0',
                'archivos-MAX_NUM_FORMS': '1000',
                'archivos-0-id': str(a.pk),
                'archivos-0-titulo': a.titulo,
                'archivos-0-tipo': a.tipo,
                'archivos-0-descripcion': '',
                'archivos-0-DELETE': 'on',
            },
        )

        self.assertEqual(r.status_code, 302)
        self.assertFalse(ArchivoTramite.objects.filter(pk=a.pk).exists())

    def test_edita_y_borra_una_direccion(self):
        t = tramite()
        d = Direccion.objects.create(
            tramite=t, lugar='Sede vieja', municipio=t.municipio,
            direccion='Calle Falsa 123',
        )
        # Con la validación por modalidad (SPEC 2026-11) un presencial
        # no puede quedarse sin direcciones: se deja otra viva.
        otra = Direccion.objects.create(
            tramite=t, lugar='Sede nueva', municipio=t.municipio,
            direccion='Av. Siempre Viva 742',
        )

        r = self.client.post(
            reverse('panel_tramite_editar', args=[t.pk]), {
                'titulo': t.titulo, 'tema': t.tema.pk,
                'modalidad': t.modalidad, 'municipios': [t.municipio.pk],
                'organismo': t.organismo.pk, 'descripcion': t.descripcion,
                'destacado': '', 'activo': 'on',
                'requisitos-TOTAL_FORMS': '0',
                'requisitos-INITIAL_FORMS': '0',
                'requisitos-MIN_NUM_FORMS': '0',
                'requisitos-MAX_NUM_FORMS': '1000',
                'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
                'enlaces-MIN_NUM_FORMS': '0',
                'enlaces-MAX_NUM_FORMS': '1000',
                'direcciones-TOTAL_FORMS': '2',
                'direcciones-INITIAL_FORMS': '2',
                'direcciones-MIN_NUM_FORMS': '0',
                'direcciones-MAX_NUM_FORMS': '1000',
                'direcciones-0-id': str(d.pk),
                'direcciones-0-lugar': d.lugar,
                'direcciones-0-municipio': d.municipio.pk,
                'direcciones-0-direccion': d.direccion,
                'direcciones-0-DELETE': 'on',
                'direcciones-1-id': str(otra.pk),
                'direcciones-1-lugar': otra.lugar,
                'direcciones-1-municipio': otra.municipio.pk,
                'direcciones-1-direccion': otra.direccion,
            },
        )

        self.assertEqual(r.status_code, 302)
        self.assertFalse(Direccion.objects.filter(pk=d.pk).exists())
        self.assertTrue(Direccion.objects.filter(pk=otra.pk).exists())

    def test_solo_pasa_el_tramite_si_los_datos_no_cierran(self):
        total_antes = Tramite.objects.count()

        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': '',  # obligatorio
            'tema': '', 'modalidad': '', 'municipios': '', 'organismo': '',
            'descripcion': '',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 200)  # vuelve con errores
        self.assertContains(r, 'errores')
        self.assertEqual(Tramite.objects.count(), total_antes)

    def test_edita_los_datos_y_agrega_un_requisito(self):
        t = tramite()
        req = t.requisitos.first()

        r = self.client.post(
            reverse('panel_tramite_editar', args=[t.pk]), {
                'titulo': 'Renovación de DNI (editado)',
                'tema': t.tema.pk,
                'modalidad': t.modalidad,
                'municipios': [t.municipio.pk],
                'organismo': t.organismo.pk,
                'descripcion': 'Descripción actualizada.',
                'destacado': '', 'activo': 'on',
                'requisitos-TOTAL_FORMS': '2',
                'requisitos-INITIAL_FORMS': '1',
                'requisitos-MIN_NUM_FORMS': '0',
                'requisitos-MAX_NUM_FORMS': '1000',
                'requisitos-0-id': str(req.pk),
                'requisitos-0-descripcion': req.descripcion,
                'requisitos-0-orden': '1',
                'requisitos-1-descripcion': 'Foto 4x4 fondo blanco',
                'requisitos-1-orden': '2',
                'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
                'enlaces-MIN_NUM_FORMS': '0',
                'enlaces-MAX_NUM_FORMS': '1000',
            },
        )

        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.titulo, 'Renovación de DNI (editado)')
        self.assertEqual(t.requisitos.count(), 2)

    def test_marcar_eliminar_borra_el_requisito_al_guardar(self):
        """La casilla «Eliminar» borra la fila: no queda un requisito vacío."""
        t = tramite()
        req = t.requisitos.first()

        r = self.client.post(reverse('panel_tramite_editar', args=[t.pk]), {
            'titulo': t.titulo,
            'tema': t.tema.pk,
            'modalidad': t.modalidad,
            'municipios': [t.municipio.pk],
            'organismo': t.organismo.pk,
            'descripcion': t.descripcion,
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '1',
            'requisitos-INITIAL_FORMS': '1',
            'requisitos-MIN_NUM_FORMS': '0',
            'requisitos-MAX_NUM_FORMS': '1000',
            'requisitos-0-id': str(req.pk),
            'requisitos-0-descripcion': req.descripcion,
            'requisitos-0-DELETE': 'on',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0',
            'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 302)
        self.assertFalse(t.requisitos.exists())

    def test_puede_publicar_desactivar_y_destacar(self):
        t = tramite(activo=False)

        r = self.client.post(reverse('panel_tramite_estado', args=[t.pk]),
                             {'accion': 'activar'})
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertTrue(t.activo)

        self.client.post(reverse('panel_tramite_estado', args=[t.pk]),
                         {'accion': 'destacar'})
        t.refresh_from_db()
        self.assertTrue(t.destacado)

        self.client.post(reverse('panel_tramite_estado', args=[t.pk]),
                         {'accion': 'desactivar'})
        t.refresh_from_db()
        self.assertFalse(t.activo)

    def test_una_accion_de_estado_desconocida_no_toca_nada(self):
        t = tramite(activo=True)

        r = self.client.post(reverse('panel_tramite_estado', args=[t.pk]),
                             {'accion': 'borrar'})

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('panel_tramites'))
        t.refresh_from_db()
        self.assertTrue(t.activo)

    def test_las_acciones_de_estado_solo_admiten_post(self):
        t = tramite()

        r = self.client.get(reverse('panel_tramite_estado', args=[t.pk]))

        self.assertEqual(r.status_code, 405)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TicketsDelDashboardTests(TestCase):
    """Tickets internos: el administrativo los abre y ve los suyos; el
    administrador y el superusuario los leen, responden y cierran.

    Son un canal aparte de las consultas ciudadanas.
    """

    def setUp(self):
        self.gestora = administrativo(username='gestora')
        self.client.force_login(self.gestora)

    def test_el_dashboard_no_tiene_el_formulario_de_tickets(self):
        """Los tickets viven en su página del menú, no en el resumen."""
        r = self.client.get(reverse('panel'))

        self.assertContains(r, reverse('panel_tickets'))
        self.assertNotContains(r, 'Tickets internos')
        self.assertNotContains(r, 'name="asunto"')

    def test_crea_un_ticket_con_asunto_descripcion_y_dos_adjuntos(self):
        r = self.client.post(reverse('panel_tickets'), {
            'asunto': 'Error al publicar un trámite',
            'descripcion': 'El botón de publicar no responde.',
            'archivos': [
                SimpleUploadedFile(
                    'captura.png', b'\x89PNG contenido',
                    content_type='image/png',
                ),
                SimpleUploadedFile(
                    'detalle.pdf', b'%PDF-1.4 contenido',
                    content_type='application/pdf',
                ),
            ],
        })

        ticket = Ticket.objects.get()
        self.assertRedirects(
            r, reverse('panel_ticket_detalle', args=[ticket.pk])
        )
        self.assertEqual(ticket.asunto, 'Error al publicar un trámite')
        self.assertEqual(
            ticket.descripcion, 'El botón de publicar no responde.'
        )
        self.assertEqual(ticket.creado_por, self.gestora)
        self.assertEqual(ticket.adjuntos.count(), 2)
        self.assertEqual(
            {a.nombre for a in ticket.adjuntos.all()},
            {'captura.png', 'detalle.pdf'},
        )

    def test_sin_adjuntos_tambien_se_guarda(self):
        r = self.client.post(reverse('panel_tickets'), {
            'asunto': 'Solo texto',
            'descripcion': 'No hace falta adjuntar nada.',
        })

        ticket = Ticket.objects.get()
        self.assertRedirects(
            r, reverse('panel_ticket_detalle', args=[ticket.pk])
        )
        self.assertEqual(ticket.adjuntos.count(), 0)

    def test_sin_asunto_no_se_crea(self):
        r = self.client.post(reverse('panel_tickets'), {
            'asunto': '', 'descripcion': 'Falta el asunto.',
        })

        self.assertEqual(r.status_code, 200)
        self.assertFalse(Ticket.objects.exists())

    def test_cada_administrativo_ve_solo_sus_tickets(self):
        otro = administrativo(username='otro')
        Ticket.objects.create(
            asunto='Ticket ajeno', descripcion='...', creado_por=otro,
        )
        Ticket.objects.create(
            asunto='Ticket propio', descripcion='...', creado_por=self.gestora,
        )

        r = self.client.get(reverse('panel_tickets'))

        self.assertContains(r, 'Ticket propio')
        self.assertNotContains(r, 'Ticket ajeno')

    def test_el_administrador_ve_los_tickets_pero_no_los_crea(self):
        """El administrador lee y gestiona; abrir tickets es del administrativo."""
        otro = administrativo(username='otro')
        Ticket.objects.create(
            asunto='Ticket del administrativo', descripcion='...',
            creado_por=otro,
        )
        self.client.force_login(administrador(username='jefazo'))

        r = self.client.get(reverse('panel_tickets'))
        self.assertContains(r, 'Ticket del administrativo')
        # No tiene el formulario de alta.
        self.assertNotContains(r, 'name="asunto"')

        self.client.post(reverse('panel_tickets'), {
            'asunto': 'No corresponde', 'descripcion': '...',
        })
        self.assertEqual(Ticket.objects.count(), 1)

    def test_el_superusuario_ve_los_tickets_de_todos(self):
        otro = administrativo(username='otro')
        Ticket.objects.create(
            asunto='Ticket de otro', descripcion='...', creado_por=otro,
        )
        self.client.force_login(superusuario())

        r = self.client.get(reverse('panel_tickets'))

        self.assertContains(r, 'Ticket de otro')

    def test_elimina_su_propio_ticket(self):
        ticket = Ticket.objects.create(
            asunto='Para borrar', descripcion='...', creado_por=self.gestora,
        )

        r = self.client.post(
            reverse('panel_ticket_eliminar', args=[ticket.pk])
        )

        self.assertRedirects(r, reverse('panel_tickets'))
        self.assertFalse(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_no_puede_eliminar_el_ticket_de_otro(self):
        otro = administrativo(username='otro')
        ticket = Ticket.objects.create(
            asunto='Ajeno', descripcion='...', creado_por=otro,
        )

        self.client.post(reverse('panel_ticket_eliminar', args=[ticket.pk]))

        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_el_administrador_no_elimina_tickets(self):
        ticket = Ticket.objects.create(
            asunto='Intocable', descripcion='...', creado_por=self.gestora,
        )
        self.client.force_login(administrador(username='jefazo'))

        self.client.post(reverse('panel_ticket_eliminar', args=[ticket.pk]))

        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    # --- Menú y listado ---------------------------------------------------

    def test_el_menu_lateral_tiene_tickets(self):
        for user in (self.gestora, administrador(username='jefazo'),
                     superusuario()):
            self.client.force_login(user)
            r = self.client.get(reverse('panel'))
            self.assertContains(r, reverse('panel_tickets'))
            self.assertContains(r, '>Tickets<')

    def test_el_administrativo_ve_el_listado_con_los_suyos(self):
        otro = administrativo(username='otro')
        Ticket.objects.create(
            asunto='Ticket propio', descripcion='...', creado_por=self.gestora,
        )
        Ticket.objects.create(
            asunto='Ticket ajeno', descripcion='...', creado_por=otro,
        )

        r = self.client.get(reverse('panel_tickets'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ticket propio')
        self.assertNotContains(r, 'Ticket ajeno')

    def test_el_administrador_ve_el_listado_completo(self):
        otro = administrativo(username='otro')
        Ticket.objects.create(
            asunto='Ticket de la gestora', descripcion='...',
            creado_por=self.gestora,
        )
        Ticket.objects.create(
            asunto='Ticket de otro', descripcion='...', creado_por=otro,
        )
        self.client.force_login(administrador(username='jefazo'))

        r = self.client.get(reverse('panel_tickets'))

        self.assertContains(r, 'Ticket de la gestora')
        self.assertContains(r, 'Ticket de otro')

    def test_el_listado_filtra_por_estado(self):
        Ticket.objects.create(
            asunto='Pendiente de revisión', descripcion='...',
            creado_por=self.gestora,
        )
        Ticket.objects.create(
            asunto='Ya resuelto', descripcion='...', creado_por=self.gestora,
            estado=Ticket.Estado.CERRADO,
        )

        r = self.client.get(reverse('panel_tickets'), {'estado': 'cerrado'})

        self.assertContains(r, 'Ya resuelto')
        self.assertNotContains(r, 'Pendiente de revisión')

    # --- Lectura, respuesta y cierre --------------------------------------

    def test_el_administrativo_lee_su_ticket(self):
        ticket = Ticket.objects.create(
            asunto='Mi ticket', descripcion='Detalle del ticket.',
            creado_por=self.gestora,
        )

        r = self.client.get(
            reverse('panel_ticket_detalle', args=[ticket.pk])
        )

        self.assertContains(r, 'Detalle del ticket.')

    def test_el_administrativo_no_abre_tickets_ajenos(self):
        otro = administrativo(username='otro')
        ticket = Ticket.objects.create(
            asunto='Ajeno', descripcion='...', creado_por=otro,
        )

        r = self.client.get(
            reverse('panel_ticket_detalle', args=[ticket.pk])
        )

        self.assertEqual(r.status_code, 404)

    def test_el_administrador_responde_un_ticket(self):
        ticket = Ticket.objects.create(
            asunto='Necesita respuesta', descripcion='...',
            creado_por=self.gestora,
        )
        self.client.force_login(administrador(username='jefazo'))

        r = self.client.post(
            reverse('panel_ticket_detalle', args=[ticket.pk]),
            {'accion': 'responder', 'respuesta': 'Ya lo revisamos y quedó resuelto.'},
        )

        self.assertRedirects(
            r, reverse('panel_ticket_detalle', args=[ticket.pk])
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, Ticket.Estado.RESPONDIDO)
        self.assertIn('quedó resuelto', ticket.respuesta)
        self.assertIsNotNone(ticket.fecha_respuesta)
        self.assertEqual(ticket.respondido_por.username, 'jefazo')

    def test_el_administrador_cierra_y_reabre_un_ticket(self):
        ticket = Ticket.objects.create(
            asunto='Para cerrar', descripcion='...', creado_por=self.gestora,
        )
        self.client.force_login(administrador(username='jefazo'))
        url = reverse('panel_ticket_detalle', args=[ticket.pk])

        self.client.post(url, {'accion': 'cerrar'})
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, Ticket.Estado.CERRADO)

        self.client.post(url, {'accion': 'reabrir'})
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)

    def test_el_administrativo_no_responde_ni_cierra(self):
        ticket = Ticket.objects.create(
            asunto='Solo lectura', descripcion='...', creado_por=self.gestora,
        )
        url = reverse('panel_ticket_detalle', args=[ticket.pk])

        self.client.post(url, {
            'accion': 'responder', 'respuesta': 'Me respondo solo.',
        })
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)
        self.assertEqual(ticket.respuesta, '')

        self.client.post(url, {'accion': 'cerrar'})
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)

    def test_el_administrativo_ve_la_respuesta_del_admin(self):
        ticket = Ticket.objects.create(
            asunto='Respondido', descripcion='...', creado_por=self.gestora,
            estado=Ticket.Estado.RESPONDIDO,
            respuesta='Respuesta del administrador.',
        )

        r = self.client.get(
            reverse('panel_ticket_detalle', args=[ticket.pk])
        )

        self.assertContains(r, 'Respuesta del administrador.')


class FormularioPorEtapasTests(TestCase):
    """SPEC 2026-11: formulario por etapas, municipios múltiples,
    exigencias de modalidad y botón «Nuevo trámite» en el panel."""

    def setUp(self):
        self.admin = administrador()
        self.client.force_login(self.admin)

    def test_el_form_se_muestra_por_etapas(self):
        """Un mismo URL, cinco secciones y navegación de ida y vuelta."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'data-pasos-tramite')
        for nombre in ('datos', 'requisitos', 'enlaces', 'direcciones',
                       'archivos'):
            self.assertContains(r, 'data-paso="%s"' % nombre)
            self.assertContains(r, 'data-ir="%s"' % nombre)
        self.assertContains(r, 'data-atras')
        self.assertContains(r, 'data-siguiente')
        self.assertContains(r, 'data-enviar')
        # La baja de URL no cambia: la creación sigue en /panel/tramites/nuevo/
        self.assertEqual(r.resolver_match.func.__name__, 'panel_tramite_nuevo')

    def test_las_etapas_condicionales_dependen_de_la_modalidad(self):
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r,
            'data-solo-modalidad="virtual,mixta"')
        self.assertContains(r,
            'data-solo-modalidad="presencial,mixta"')

    def test_la_fila_de_requisitos_se_denomina_requisitos_1(self):
        """El requisito ya no se llama «Descripción»: aparece «Requisito 1»."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'Requisitos <span data-numero>1</span>')
        self.assertContains(r, 'Contenido del requisito')
        self.assertNotContains(r, '<label for="id_requisitos-0-descripcion">Descripción</label>')

    def test_se_pueden_elegir_varios_municipios(self):
        """Municipios múltiples: todos quedan relacionados al trámite."""
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Trámite en dos municipios',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio('Candelaria').pk, municipio('Azara').pk],
            'organismo': organismo().pk,
            'descripcion': 'Se puede hacer en ambos',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Trámite en dos municipios')
        self.assertEqual(
            {m.nombre for m in nuevo.municipios.all()},
            {'Candelaria', 'Azara'},
        )
        # El municipio principal (FK) queda dentro de los elegidos: la
        # ficha pública sigue mostrando un municipio real.
        self.assertIn(nuevo.municipio, nuevo.municipios.all())

    def test_al_editarse_la_seleccion_de_municipios_se_actualiza(self):
        t = tramite()
        azara = municipio('Azara')

        self.client.post(reverse('panel_tramite_editar', args=[t.pk]), {
            'titulo': t.titulo, 'tema': t.tema.pk,
            'modalidad': t.modalidad, 'municipios': [t.municipio.pk,
                                                     azara.pk],
            'organismo': t.organismo.pk, 'descripcion': t.descripcion,
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        t.refresh_from_db()
        azara.refresh_from_db()
        self.assertEqual(t.municipios.count(), 2)
        self.assertIn(azara, t.municipios.all())

    def test_con_modalidad_virtual_se_exigen_enlaces(self):
        total_antes = Tramite.objects.count()

        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Turnos virtuales',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'virtual',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se pide en línea',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'al menos un enlace oficial')
        self.assertEqual(Tramite.objects.count(), total_antes)

    def test_con_modalidad_presencial_se_exigen_direcciones(self):
        total_antes = Tramite.objects.count()

        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Renovación presencial',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se pide en una oficina',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'direcciones-TOTAL_FORMS': '0', 'direcciones-INITIAL_FORMS': '0',
            'direcciones-MIN_NUM_FORMS': '0',
            'direcciones-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'al menos una dirección de atención')
        self.assertEqual(Tramite.objects.count(), total_antes)

    def test_un_enlace_incompleto_corta_el_guardado(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'DNI virtual',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'virtual',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se pide online',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '1', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
            'enlaces-0-nombre': 'Pedir turno',   # sin URL
        })

        self.assertEqual(r.status_code, 200)
        self.assertFalse(Tramite.objects.filter(titulo='DNI virtual').exists())

    def test_sin_archivos_se_puede_crear_normalmente(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Reclamo por luz',
            'tema': Tema.objects.get_or_create(nombre='Impuestos')[0].pk,
            'modalidad': 'presencial',
            'municipios': [municipio().pk],
            'organismo': organismo().pk,
            'descripcion': 'Se hace presencialmente',
            'destacado': '', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
            'direcciones-TOTAL_FORMS': '1', 'direcciones-INITIAL_FORMS': '0',
            'direcciones-MIN_NUM_FORMS': '0',
            'direcciones-MAX_NUM_FORMS': '1000',
            'direcciones-0-lugar': 'Oficina de la comuna',
            'direcciones-0-municipio': municipio().pk,
            'direcciones-0-direccion': 'Av. Mitre 100',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = Tramite.objects.get(titulo='Reclamo por luz')
        self.assertEqual(nuevo.archivos.count(), 0)
        self.assertEqual(nuevo.direcciones.count(), 1)

    def test_cada_elemento_agregado_tiene_su_boton_de_eliminar(self):
        """SPEC 4: cada fila de requisitos, enlaces, direcciones y archivos
        tiene su propio botón «✕ Eliminar»."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'data-quitar-fila')
        self.assertContains(r, '✕ Eliminar')
        # Una por sección: el botón viaja en la fila, no uno general.
        for seccion in ('requisitos', 'enlaces', 'direcciones', 'archivos'):
            self.assertContains(r, 'data-filas="%s"' % seccion)

    def test_el_boton_nuevo_tramite_esta_en_el_panel(self):
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'Nuevo trámite')
        self.assertContains(r, reverse('panel_tramite_nuevo'))

    def test_los_municipios_de_la_lista_completa_estan_disponibles(self):
        """La SPEC enumera los municipios: la migración los cargó a la base."""
        from munitramites.models import Municipio as ModeloMunicipio

        nombres = set(ModeloMunicipio.objects.values_list('nombre', flat=True))

        for nombre in (
            'Posadas', 'Oberá', 'Eldorado', 'Puerto Iguazú', 'Apóstoles',
            'Candelaria', 'San Vicente', 'Comandante Andresito', 'Azara',
            'Leandro N. Alem', '25 de Mayo', 'Jardín América', 'Garupá',
        ):
            self.assertIn(nombre, nombres)

        self.assertEqual(len(nombres), 69)


class CentroDeConsultasTests(TestCase):
    """Ver todas las consultas y responder (RF-10)."""

    def setUp(self):
        self.admin = administrador()
        self.client.force_login(self.admin)
        self.autor = ciudadano(username='ana')
        self.consulta = Consulta.objects.create(
            usuario=self.autor, asunto='Duda de Ana',
            contenido='¿Que documentos necesito para el DNI?',
        )

    def test_ve_las_consultas_de_todos(self):
        r = self.client.get(reverse('panel_consultas'))

        self.assertContains(r, 'Duda de Ana')
        self.assertContains(r, 'ana')

    def test_en_la_lista_se_ve_quien_la_mando(self):
        """Nombre, id y correo del emisor: con eso se ubica al que preguntó."""
        r = self.client.get(reverse('panel_consultas'))

        self.assertContains(r, self.autor.username)
        self.assertContains(r, self.autor.email)
        self.assertContains(r, str(self.autor.perfil.id))

    def test_en_la_ficha_se_ve_quien_la_mando(self):
        r = self.client.get(
            reverse('panel_consulta', args=[self.consulta.pk])
        )

        self.assertContains(r, self.autor.username)
        self.assertContains(r, self.autor.email)
        self.assertContains(r, str(self.autor.perfil.id))

    def test_el_filtro_por_estado_anda(self):
        Consulta.objects.create(
            asunto='Ya respondida', contenido='Gracias por todo.',
            estado='respondido',
        )

        r = self.client.get(reverse('panel_consultas') + '?estado=pendiente')

        self.assertContains(r, 'Duda de Ana')
        self.assertNotContains(r, 'Ya respondida')

    def test_responder_cambia_el_estado(self):
        r = self.client.post(
            reverse('panel_consulta', args=[self.consulta.pk]),
            {'respuesta': 'Necesitás el DNI vigente y el formulario.'},
        )

        self.assertEqual(r.status_code, 302)
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.estado, 'respondido')
        self.assertIn('DNI vigente', self.consulta.respuesta)

    def test_sin_respuesta_valida_no_se_cambia_nada(self):
        r = self.client.post(
            reverse('panel_consulta', args=[self.consulta.pk]),
            {'respuesta': 'no'},  # mínimo 5 caracteres
        )

        self.assertEqual(r.status_code, 200)  # vuelve con el error
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.estado, 'pendiente')
        self.assertEqual(self.consulta.respuesta, '')

    def test_en_la_ficha_se_ve_lo_que_escribio_el_ciudadano(self):
        r = self.client.get(
            reverse('panel_consulta', args=[self.consulta.pk])
        )

        self.assertContains(r, 'Duda de Ana')
        self.assertContains(r, '¿Que documentos necesito para el DNI?')


class UsuariosTests(TestCase):
    """Alta de cuentas y gestión de roles, sin tocar al superusuario."""

    def setUp(self):
        self.admin = administrador()
        self.jefe = superusuario()
        self.client.force_login(self.admin)

    def test_el_listado_trae_a_todos(self):
        ciudadano(username='ana')

        r = self.client.get(reverse('panel_usuarios'))

        self.assertContains(r, 'ana')
        self.assertContains(r, 'admin')
        self.assertContains(r, 'jefe')

    def test_la_busqueda_filtra(self):
        ciudadano(username='ana')
        ciudadano(username='juan', email='juan@x.test')

        r = self.client.get(reverse('panel_usuarios') + '?q=juan')

        self.assertContains(r, 'juan')
        self.assertNotContains(r, '>ana<')

    def test_crea_un_administrador(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'gestor', 'email': 'gestor@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'administrador',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='gestor')
        self.assertTrue(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        # El rol queda guardado en su perfil (que se identifica con un UUID)
        self.assertEqual(nuevo.perfil.rol, 'administrador')
        self.assertIsInstance(nuevo.perfil.pk, uuid.UUID)

    def test_crea_un_usuario_comun(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'ciudadana', 'email': 'c@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'corriente',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='ciudadana')
        self.assertFalse(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertEqual(nuevo.perfil.rol, 'corriente')

    def test_el_form_de_alta_nunca_ofrece_ser_superusuario(self):
        r = self.client.get(reverse('panel_usuario_nuevo'))

        self.assertNotContains(r, 'is_superuser')

    def test_no_puede_crear_un_superusuario_ni_si_lo_pide_en_el_post(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'hacker', 'email': 'h@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'administrador',
            'is_superuser': 'on',  # el campo ni existe en el form
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='hacker')
        self.assertFalse(nuevo.is_superuser)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_cambia_el_rol_de_una_cuenta(self):
        objetivo = ciudadano(username='ana')

        r = self.client.post(
            reverse('panel_usuario_editar', args=[objetivo.pk]), {
                'username': 'ana', 'email': 'ana@munitramites.test',
                'is_active': 'on', 'rol': 'administrador',
            },
        )

        self.assertEqual(r.status_code, 302)
        objetivo.refresh_from_db()
        self.assertTrue(objetivo.is_staff)
        self.assertFalse(objetivo.is_superuser)

    def test_nadie_se_vuelve_superusuario_desde_el_form_de_rol(self):
        objetivo = ciudadano(username='ana')

        self.client.post(
            reverse('panel_usuario_editar', args=[objetivo.pk]), {
                'username': 'ana', 'email': 'ana@munitramites.test',
                'is_active': 'on', 'rol': 'administrador',
                'is_superuser': 'on',
            },
        )

        objetivo.refresh_from_db()
        self.assertFalse(objetivo.is_superuser)

    def test_no_puede_editar_al_superusuario(self):
        r = self.client.get(
            reverse('panel_usuario_editar', args=[self.jefe.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('panel_usuarios'))

        r = self.client.post(
            reverse('panel_usuario_editar', args=[self.jefe.pk]),
            {'username': 'jefe', 'email': 'x@x.test',
             'is_active': 'on', 'rol': 'corriente'},
            follow=True,
        )

        self.assertContains(r, 'no se puede editar')
        self.jefe.refresh_from_db()
        self.assertTrue(self.jefe.is_superuser)
        self.assertTrue(self.jefe.is_staff)

    def test_no_puede_eliminar_al_superusuario(self):
        r = self.client.post(
            reverse('panel_usuario_eliminar', args=[self.jefe.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.jefe.pk).exists())

    def test_no_puede_editarse_a_si_mismo(self):
        r = self.client.get(
            reverse('panel_usuario_editar', args=[self.admin.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('panel_usuarios'))

    def test_no_puede_eliminarse_a_si_mismo(self):
        r = self.client.post(
            reverse('panel_usuario_eliminar', args=[self.admin.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_elimina_una_cuenta_con_su_perfil(self):
        objetivo = ciudadano(username='ana')
        clave_perfil = objetivo.perfil.pk

        r = self.client.post(
            reverse('panel_usuario_eliminar', args=[objetivo.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertFalse(User.objects.filter(username='ana').exists())
        self.assertFalse(Perfil.objects.filter(pk=clave_perfil).exists())

    def test_crea_un_usuario_administrativo(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'ayudante', 'email': 'ayudante@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'administrativo',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='ayudante')
        self.assertTrue(nuevo.is_staff)   # entra al panel…
        self.assertEqual(nuevo.perfil.rol, 'administrativo')
        self.assertFalse(nuevo.is_superuser)  # …pero jamás el super

    def test_mover_a_administrativo_no_pierde_el_panel(self):
        objetivo = administrador(username='otro')

        r = self.client.post(
            reverse('panel_usuario_editar', args=[objetivo.pk]), {
                'username': 'otro', 'email': 'otro@munitramites.test',
                'is_active': 'on', 'rol': 'administrativo',
            },
        )

        self.assertEqual(r.status_code, 302)
        objetivo.refresh_from_db()
        self.assertTrue(objetivo.is_staff)
        self.assertEqual(objetivo.perfil.rol, 'administrativo')

    def test_la_lista_muestra_los_tres_roles(self):
        ciudadano(username='ana')
        administrativo(username='jorge')

        r = self.client.get(reverse('panel_usuarios'))

        self.assertContains(r, 'etiqueta--administrador')
        self.assertContains(r, 'etiqueta--administrativo')
        self.assertContains(r, 'etiqueta--usuario')   # corriente
        self.assertContains(r, 'etiqueta--superusuario')


class TemasTests(TestCase):
    """Alta de temas desde el panel (RF-07)."""

    def setUp(self):
        self.client.force_login(administrador())

    def test_crea_un_tema(self):
        r = self.client.post(reverse('panel_temas'),
                             {'nombre': 'Medio Ambiente'})

        self.assertEqual(r.status_code, 302)
        self.assertTrue(Tema.objects.filter(nombre='Medio Ambiente').exists())

    def test_un_tema_repetido_no_pasa(self):
        Tema.objects.get_or_create(nombre='Documentación')
        total = Tema.objects.count()

        r = self.client.post(reverse('panel_temas'),
                             {'nombre': 'Documentación'})

        self.assertEqual(r.status_code, 200)  # vuelve con el error
        self.assertEqual(Tema.objects.count(), total)

    def test_los_temas_y_los_tramites_que_usa(self):
        tramite(tema='Tránsito')
        tramite(titulo='Otro trámite', tema='Documentación')

        r = self.client.get(reverse('panel_temas'))

        self.assertContains(r, 'Tránsito')
        self.assertContains(r, 'Documentación')
        self.assertContains(r, 'Medio')  # el form de alta está en la página


class DashboardTests(TestCase):
    """El resumen general: contadores y gráficos del tablero."""

    def setUp(self):
        self.client.force_login(administrador())

    def test_el_resumen_trae_el_tablero_completo(self):
        tramite('Renovacion de DNI')
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'pn-resumen')
        self.assertContains(r, 'pn-bienvenida')
        self.assertContains(r, 'Trámites por tema')
        self.assertContains(r, 'Consultas por estado')
        self.assertContains(r, 'Trámites por modalidad')

    def test_el_anillo_pinta_un_tramo_por_estado(self):
        Consulta.objects.create(asunto='Una consulta', contenido='Hola')
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'conic-gradient(')
        for color in ('var(--m-rojo)', 'var(--m-verde)', 'var(--m-azul)'):
            self.assertContains(r, color)

    def test_sin_datos_los_graficos_no_rompen(self):
        r = self.client.get(reverse('panel'))

        # Sin consultas el anillo queda gris y ninguna barra divide por cero.
        self.assertContains(r, 'conic-gradient(var(--s-ln) 0 100%)')
        self.assertEqual(r.status_code, 200)

    def test_el_resumen_muestra_los_ultimos_movimientos(self):
        t = tramite('Cambio de domicilio')
        Consulta.objects.create(
            asunto='No me llego el turno', contenido='Detalle',
            tramite=t, usuario=ciudadano(),
        )
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'Cambio de domicilio')
        self.assertContains(r, 'No me llego el turno')


class DashboardDatosTests(TestCase):
    """Indicadores, filtros, ranking y actividad calculados con datos reales."""

    def setUp(self):
        self.client.force_login(administrador())

    def test_los_indicadores_salen_de_la_base(self):
        tramite('Trámite publicado')
        tramite('Trámite retirado', activo=False)
        Consulta.objects.create(asunto='Pendiente', contenido='Hola')
        respondida = Consulta.objects.create(
            asunto='Respondida', contenido='Hola',
            estado=Consulta.Estado.RESPONDIDO,
        )
        respondida.estado = Consulta.Estado.RESPONDIDO
        respondida.save(update_fields=['estado'])
        ciudadano()

        r = self.client.get(reverse('panel'))

        self.assertEqual(r.context['tramites_total'], 2)
        self.assertEqual(r.context['tramites_activos'], 1)
        self.assertEqual(r.context['tramites_inactivos'], 1)
        self.assertEqual(r.context['consultas_total'], 2)
        self.assertEqual(r.context['consultas_pendientes'], 1)
        self.assertEqual(r.context['usuarios'], 1)

    def test_el_filtro_de_periodo_deja_afuera_lo_viejo(self):
        vieja = Consulta.objects.create(asunto='Vieja', contenido='Hola')
        Consulta.objects.filter(pk=vieja.pk).update(
            fecha=timezone.now() - timedelta(days=90)
        )
        Consulta.objects.create(asunto='Nueva', contenido='Hola')

        r = self.client.get(reverse('panel'), {'periodo': '30d'})
        self.assertEqual(r.context['consultas_total'], 1)

        r = self.client.get(reverse('panel'), {'periodo': 'todo'})
        self.assertEqual(r.context['consultas_total'], 2)

        r = self.client.get(reverse('panel'), {
            'desde': (timezone.localdate() - timedelta(days=100)).isoformat(),
            'hasta': timezone.localdate().isoformat(),
        })
        self.assertEqual(r.context['consultas_total'], 2)
        self.assertTrue(r.context['filtros']['personalizado'])

    def test_los_filtros_de_estado_municipio_y_modalidad(self):
        posadas = municipio('Posadas')
        obera = municipio('Oberá')
        presencial = tramite(
            'Presencial en Posadas', municipio=posadas, modalidad='presencial',
        )
        virtual = tramite(
            'Virtual en Oberá', municipio=obera, modalidad='virtual',
        )
        Consulta.objects.create(
            asunto='De Posadas', contenido='Hola', tramite=presencial,
        )
        Consulta.objects.create(
            asunto='De Oberá', contenido='Hola', tramite=virtual,
            estado=Consulta.Estado.RESPONDIDO,
        )

        r = self.client.get(reverse('panel'), {'estado': 'respondido'})
        self.assertEqual(r.context['consultas_grafico_total'], 1)

        r = self.client.get(reverse('panel'), {'municipio': obera.pk})
        self.assertEqual(r.context['consultas_total'], 1)
        self.assertEqual(r.context['tramites_total'], 1)

        r = self.client.get(reverse('panel'), {'modalidad': 'virtual'})
        self.assertEqual(r.context['tramites_total'], 1)
        self.assertEqual(r.context['consultas_total'], 1)

    def test_el_ranking_y_los_municipios_cuentan_las_consultas(self):
        t = tramite('Trámite más consultado')
        otro = tramite('Otro trámite')
        for asunto in ('Uno', 'Dos', 'Tres'):
            Consulta.objects.create(
                asunto=asunto, contenido='Hola', tramite=t,
            )
        Consulta.objects.create(
            asunto='Cuatro', contenido='Hola', tramite=otro,
        )

        r = self.client.get(reverse('panel', ), {'periodo': 'todo'})

        self.assertEqual(r.context['ranking'][0]['pk'], t.pk)
        self.assertEqual(r.context['ranking'][0]['n'], 3)
        self.assertEqual(r.context['por_municipio'][0]['n'], 4)

    def test_la_actividad_incluye_la_respuesta_de_una_consulta(self):
        consulta = Consulta.objects.create(
            asunto='Necesito una respuesta', contenido='Hola',
        )

        self.client.post(
            reverse('panel_consulta', args=[consulta.pk]),
            {'respuesta': 'Te respondemos por acá.'},
        )

        consulta.refresh_from_db()
        self.assertIsNotNone(consulta.fecha_respuesta)
        self.assertEqual(consulta.respondido_por.username, 'admin')

        r = self.client.get(reverse('panel'))
        self.assertContains(r, 'Consulta respondida')
        self.assertEqual(r.context['respuestas_medidas'], 1)
        self.assertTrue(r.context['promedio_respuesta'])

    def test_los_estados_vacios_no_inventan_datos(self):
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'No hay consultas registradas en este período.')
        self.assertContains(r, 'Sin datos')
        self.assertContains(r, 'No hay movimientos registrados en este período.')
        self.assertEqual(r.context['promedio_respuesta'], '')

    def test_el_administrativo_ve_solo_sus_tickets_y_no_las_cuentas(self):
        admin = administrador(username='jefe')
        gestor = administrativo(username='gestor')
        Ticket.objects.create(
            asunto='Del administrador', descripcion='Hola', creado_por=admin,
        )
        Ticket.objects.create(
            asunto='Del gestor', descripcion='Hola', creado_por=gestor,
        )
        self.client.force_login(gestor)

        r = self.client.get(reverse('panel'))

        self.assertEqual(r.context['tickets_total'], 1)
        self.assertEqual(r.context['tickets_pendientes'], 1)
        self.assertNotContains(r, reverse('panel_usuarios'))

    def test_el_endpoint_devuelve_solo_el_contenido(self):
        Consulta.objects.create(asunto='Una consulta', contenido='Hola')

        r = self.client.get(
            reverse('panel_dashboard_datos'), {'periodo': 'todo'}
        )

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'pn-dashboard-contenido')
        self.assertContains(r, 'Consultas por período')
        self.assertNotContains(r, 'pn-menu')

    def test_el_endpoint_respeta_los_permisos(self):
        self.client.force_login(ciudadano())

        r = self.client.get(reverse('panel_dashboard_datos'))

        self.assertEqual(r.status_code, 302)


class DisenoTests(TestCase):
    """El panel usa el layout propio: menú lateral, tablas y el CSS del sitio."""

    def setUp(self):
        self.client.force_login(administrador())

    def test_el_menu_de_seccion_esta_en_todas_las_paginas(self):
        for nombre in ('panel', 'panel_tramites', 'panel_consultas',
                       'panel_usuarios', 'panel_temas'):
            r = self.client.get(reverse(nombre))

            self.assertContains(r, 'class="pn-menu"', msg_prefix=nombre)
            self.assertContains(r, 'Centro de Trámites', msg_prefix=nombre)
            self.assertContains(r, 'Centro de Consultas', msg_prefix=nombre)

    def test_el_item_de_usuarios_solo_lo_ve_el_administrador(self):
        self.client.force_login(administrativo())
        r = self.client.get(reverse('panel'))
        self.assertNotContains(r, reverse('panel_usuarios'))
        self.assertNotContains(r, 'Nuevo usuario')

        # la cuenta que ya creó setUp (rol administrador)
        self.client.force_login(User.objects.get(username='admin'))
        r = self.client.get(reverse('panel'))
        self.assertContains(r, reverse('panel_usuarios'))

    def test_el_menu_marca_la_seccion_actual(self):
        r = self.client.get(reverse('panel_consultas'))

        self.assertContains(r, 'pn-menu__item activo')

    def test_el_header_y_el_pie_linkean_al_panel(self):
        r = self.client.get(reverse('inicio'))

        self.assertContains(r, 'href="%s"' % reverse('panel'))

    def test_todo_se_pinta_con_el_css_propio(self):
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'css/app.css')
        self.assertContains(r, 'css/panel.css')
        # La URL lleva la fecha del archivo: el navegador no reusa la copia
        # vieja cuando cambia el CSS (ver templatetags/estaticos.py).
        self.assertContains(r, 'css/app.css?v=')
        self.assertContains(r, 'css/panel.css?v=')

    def test_los_formularios_del_panel_traen_el_token_csrf(self):
        for nombre in ('panel_tramite_nuevo', 'panel_usuario_nuevo',
                       'panel_temas'):
            r = self.client.get(reverse(nombre))

            self.assertContains(r, 'csrfmiddlewaretoken', msg_prefix=nombre)
