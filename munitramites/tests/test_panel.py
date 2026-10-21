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

import uuid

from django.contrib.auth.models import User
from django.urls import reverse

from munitramites.models import Consulta, Perfil, Requisito, Tema, Tramite

from .base import (
    TestCase, administrador, administrativo, ciudadano, municipio,
    organismo, superusuario, tramite,
)

# URLs del panel, para barrer el acceso en un solo test
URLS_PANEL = (
    'panel', 'panel_tramites', 'panel_tramite_nuevo', 'panel_consultas',
    'panel_usuarios', 'panel_usuario_nuevo', 'panel_temas',
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
        self.client.force_login(ciudadano(username='ana'))

        for url in (reverse('panel_tramite_editar', args=[t.pk]),
                    reverse('panel_tramite_estado', args=[t.pk]),
                    reverse('panel_consulta', args=[c.pk]),
                    reverse('panel_usuario_editar', args=[1]),
                    reverse('panel_usuario_eliminar', args=[1])):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('inicio'), url)


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
            'municipio': municipio().pk,
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
            'municipio': '',
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
        """Tres filas vacías listas y un botón que clona más (requisitos y enlaces)."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'requisitos-2-descripcion')
        self.assertContains(r, 'enlaces-2-nombre')
        self.assertContains(r, 'data-agregar-fila="requisitos"')
        self.assertContains(r, 'data-agregar-fila="enlaces"')
        self.assertContains(r, 'requisitos-__prefix__-descripcion')

    def test_los_requisitos_se_numeran_solos_y_la_fila_borrada_sale(self):
        """El número lo pone el panel y la fila «Eliminar» se saca de la lista."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertContains(r, 'data-numerar')
        self.assertContains(r, 'Requisito <span data-numero>1</span>')
        self.assertContains(r, 'data-aviso-borrado="requisito"')
        self.assertContains(r, 'data-aviso-borrado="enlace"')

    def test_los_enlaces_no_son_campos_fijos(self):
        """Cada enlace se carga como botón con nombre y URL, no hardcodeado."""
        r = self.client.get(reverse('panel_tramite_nuevo'))

        self.assertNotContains(r, 'Enlace turnos')
        self.assertNotContains(r, 'Enlace oficial')
        self.assertNotContains(r, 'name="enlace_turnos"')
        self.assertNotContains(r, 'name="enlace_oficial"')
        self.assertContains(r, 'enlaces-0-nombre')
        self.assertContains(r, 'enlaces-0-url')

    def test_crea_un_tramite_con_requisitos_y_enlaces(self):
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Pasaporte argentino',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'presencial',
            'municipio': municipio().pk,
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

    def test_solo_pasa_el_tramite_si_los_datos_no_cierran(self):
        total_antes = Tramite.objects.count()

        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': '',  # obligatorio
            'tema': '', 'modalidad': '', 'municipio': '', 'organismo': '',
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
                'municipio': t.municipio.pk,
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
            'municipio': t.municipio.pk,
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


class DisenoTests(TestCase):
    """El panel usa el layout propio: pestañas, tablas y el CSS del sitio."""

    def setUp(self):
        self.client.force_login(administrador())

    def test_las_pestanas_de_seccion_estan_en_todas_las_paginas(self):
        for nombre in ('panel', 'panel_tramites', 'panel_consultas',
                       'panel_usuarios', 'panel_temas'):
            r = self.client.get(reverse(nombre))

            self.assertContains(r, 'class="pestanas"', msg_prefix=nombre)
            self.assertContains(r, 'Centro de Trámites', msg_prefix=nombre)
            self.assertContains(r, 'Centro de Consultas', msg_prefix=nombre)

    def test_la_pestana_de_usuarios_solo_la_ve_el_administrador(self):
        self.client.force_login(administrativo())
        r = self.client.get(reverse('panel'))
        self.assertNotContains(r, reverse('panel_usuarios'))
        self.assertNotContains(r, 'Nuevo usuario')

        # la cuenta que ya creó setUp (rol administrador)
        self.client.force_login(User.objects.get(username='admin'))
        r = self.client.get(reverse('panel'))
        self.assertContains(r, reverse('panel_usuarios'))

    def test_las_pestanas_marcan_la_seccion_actual(self):
        r = self.client.get(reverse('panel_consultas'))

        self.assertContains(r, 'pestanas')

    def test_el_header_y_el_pie_linkean_al_panel(self):
        r = self.client.get(reverse('inicio'))

        self.assertContains(r, 'href="%s"' % reverse('panel'))

    def test_todo_se_pinta_con_el_css_propio(self):
        r = self.client.get(reverse('panel'))

        self.assertContains(r, 'css/app.css')
        # La URL lleva la fecha del archivo: el navegador no reusa la copia
        # vieja cuando cambia el CSS (ver templatetags/estaticos.py).
        self.assertContains(r, 'css/app.css?v=')

    def test_los_formularios_del_panel_traen_el_token_csrf(self):
        for nombre in ('panel_tramite_nuevo', 'panel_usuario_nuevo',
                       'panel_temas'):
            r = self.client.get(reverse(nombre))

            self.assertContains(r, 'csrfmiddlewaretoken', msg_prefix=nombre)
