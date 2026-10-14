"""ESP-02 / RF-03, RF-07, RF-11, RF-13 — Roles y permisos.

El documento define tres roles ACUMULATIVOS: **Usuario corriente** (ve
trámites y envía consultas), **Usuario administrativo** (además responde
consultas y edita trámites y temas) y **Usuario administrador** (además
gestiona las cuentas del sistema). El rol vive en `Perfil.rol` y
`is_staff` queda sincronizado con él: quien no es gestión no llega a
/panel/. El `/admin/` de Django queda reservado al superusuario
(middleware.py), que está fuera de los tres roles.

Criterio de aceptación: «Los usuarios solo pueden acceder a las funciones
permitidas según su rol».
"""

from django.contrib.auth.models import User

from django.urls import reverse

from munitramites.models import Consulta, Tema, Tramite, gestiona_cuentas

from .base import (
    TestCase, administrador, administrativo, ciudadano, municipio,
    organismo, superusuario, tramite,
)


class CiudadanoTests(TestCase):
    """Permisos del rol Usuario."""

    def setUp(self):
        self.user = ciudadano(username='ana')
        self.client.force_login(self.user)

    def test_entra_a_las_paginas_del_ciudadano(self):
        for url in (reverse('perfil'), reverse('consultas'),
                    reverse('consulta_nueva'), reverse('soporte'),
                    reverse('tramites'), reverse('inicio')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_no_entra_al_panel_de_administracion(self):
        r = self.client.get(reverse('admin:index'))

        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])

    def test_tampoco_entra_a_las_vistas_de_administracion(self):
        """El control es en cada vista, no solo en la portada del panel."""
        for url in (reverse('admin:munitramites_tramite_changelist'),
                    reverse('admin:munitramites_consulta_changelist'),
                    reverse('admin:auth_user_changelist')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn('/admin/login/', r['Location'])

    def test_no_entra_al_panel_propio(self):
        """/panel/ también es territorio de administradores (RF-13)."""
        for url in (reverse('panel'), reverse('panel_tramites'),
                    reverse('panel_consultas'), reverse('panel_usuarios')):
            r = self.client.get(url)

            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('inicio'), url)

    def test_le_avisa_por_que_no_pasa(self):
        r = self.client.get(reverse('panel'), follow=True)

        self.assertContains(r, 'solo para administradores')


class AdministrativoTests(TestCase):
    """Rol Usuario administrativo: el día a día del sitio, menos las cuentas."""

    def setUp(self):
        self.gestor = administrativo()
        self.client.force_login(self.gestor)

    def test_entra_a_la_gestion_del_dia_a_dia(self):
        for url in (reverse('panel'), reverse('panel_tramites'),
                    reverse('panel_tramite_nuevo'), reverse('panel_consultas'),
                    reverse('panel_temas')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_no_llega_a_la_gestion_de_cuentas(self):
        for url in (reverse('panel_usuarios'), reverse('panel_usuario_nuevo')):
            r = self.client.get(url)

            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('panel'), url)

        r = self.client.get(reverse('panel'), follow=True)
        self.assertContains(r, 'solo para usuarios administradores')

    def test_no_ve_ni_la_pestana_ni_las_tarjetas_de_usuarios(self):
        r = self.client.get(reverse('panel'))

        self.assertNotContains(r, reverse('panel_usuarios'))
        self.assertNotContains(r, 'Nuevo usuario')

    def test_edita_tramites(self):
        t = tramite()

        r = self.client.get(reverse('panel_tramite_editar', args=[t.pk]))

        self.assertEqual(r.status_code, 200)

    def test_responde_consultas_de_otros(self):
        autor = ciudadano(username='ana')
        consulta = Consulta.objects.create(
            usuario=autor, asunto='Duda de Ana',
            contenido='¿Qué documentos necesito?',
        )

        r = self.client.post(
            reverse('panel_consulta', args=[consulta.pk]),
            {'respuesta': 'El DNI vigente y el formulario.'},
        )

        self.assertEqual(r.status_code, 302)
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, 'respondido')

    def test_no_pasa_por_el_admin_de_django(self):
        """/admin/ es del superusuario: al administrativo lo manda a /panel/."""
        r = self.client.get(reverse('admin:index'))

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('panel'))

    def test_solo_el_administrador_y_el_super_gestionan_cuentas(self):
        self.assertFalse(gestiona_cuentas(ciudadano(username='ana')))
        self.assertFalse(gestiona_cuentas(self.gestor))
        self.assertTrue(gestiona_cuentas(administrador()))
        self.assertTrue(gestiona_cuentas(superusuario()))


class AdministradorTests(TestCase):
    """Permisos del rol Administrador: se ejercen desde /panel/."""

    def setUp(self):
        self.admin = administrador()
        self.client.force_login(self.admin)

    def test_entra_al_panel(self):
        r = self.client.get(reverse('panel'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Centro de Trámites')
        self.assertContains(r, 'Centro de Consultas')
        self.assertContains(r, 'Resumen general')

    def test_entra_a_los_dos_centros(self):
        for url in (reverse('panel_tramites'), reverse('panel_consultas'),
                    reverse('panel_usuarios'), reverse('panel_temas')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_no_pasa_por_el_admin_de_django(self):
        """/admin/ es del superusuario: al administrador lo manda a /panel/."""
        for url in (reverse('admin:index'),
                    reverse('admin:munitramites_tramite_changelist'),
                    reverse('admin:auth_user_changelist')):
            r = self.client.get(url)

            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('panel'), url)

    def test_al_redirigido_le_avisa_el_motivo(self):
        r = self.client.get(reverse('admin:index'), follow=True)

        self.assertContains(r, 'solo para el superusuario')
        # y ya está parado en el panel, con sus dos centros a la vista
        self.assertContains(r, 'Centro de Trámites')

    def test_puede_cargar_temas_personalizados(self):
        """RF-07: los temas se cargan desde el panel (antes: choices)."""
        r = self.client.post(reverse('panel_temas'),
                             {'nombre': 'Medio Ambiente'})

        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Tema.objects.filter(nombre='Medio Ambiente').exists()
        )

    def test_puede_gestionar_usuarios(self):
        """RF-11: consultar y administrar los usuarios registrados."""
        ciudadano(username='ana')

        r = self.client.get(reverse('panel_usuarios'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ana')

    def test_puede_crear_un_administrador_desde_el_panel(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'nuevo_admin',
            'email': 'nuevo@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'administrador',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='nuevo_admin')
        self.assertTrue(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)

    def test_puede_crear_un_usuario_comun(self):
        r = self.client.post(reverse('panel_usuario_nuevo'), {
            'username': 'ciudadana',
            'email': 'ciudadana@munitramites.test',
            'password1': 'ClaveSegura123x', 'password2': 'ClaveSegura123x',
            'rol': 'corriente',
        })

        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='ciudadana')
        self.assertFalse(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)

    def test_puede_gestionar_tramites(self):
        """RF-07: crear y editar trámites desde el panel."""
        r = self.client.post(reverse('panel_tramite_nuevo'), {
            'titulo': 'Certificado de residencia',
            'tema': Tema.objects.get_or_create(nombre='Documentación')[0].pk,
            'modalidad': 'virtual',
            'descripcion': 'Se pide en linea.',
            'municipio': municipio().pk,
            'organismo': organismo().pk,
            'enlace_turnos': '', 'enlace_oficial': '',
            'destacado': 'on', 'activo': 'on',
            'requisitos-TOTAL_FORMS': '0', 'requisitos-INITIAL_FORMS': '0',
            'requisitos-MIN_NUM_FORMS': '0', 'requisitos-MAX_NUM_FORMS': '1000',
            'enlaces-TOTAL_FORMS': '0', 'enlaces-INITIAL_FORMS': '0',
            'enlaces-MIN_NUM_FORMS': '0', 'enlaces-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Tramite.objects.filter(titulo='Certificado de residencia').exists()
        )

    def test_las_consultas_se_gestionan_desde_el_centro_de_consultas(self):
        """RF-10: ve las consultas de todos y responde desde el panel."""
        autor = ciudadano(username='ana')
        consulta = Consulta.objects.create(
            usuario=autor, asunto='Duda de Ana',
            contenido='¿Que documentos necesito?',
        )

        r = self.client.get(reverse('panel_consultas'))
        self.assertContains(r, 'Duda de Ana')

        r = self.client.post(
            reverse('panel_consulta', args=[consulta.pk]),
            {'respuesta': 'Necesitás el DNI vigente y el formulario.'},
        )

        self.assertEqual(r.status_code, 302)
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, 'respondido')
        self.assertIn('DNI vigente', consulta.respuesta)

    def test_los_organismos_quedan_para_el_superusuario(self):
        """Ese atajo del dashboard no aparece para un mero administrador."""
        r = self.client.get(reverse('panel'))

        self.assertNotContains(r, 'Django admin')
        # y el /admin/ sigue cerrado para él
        self.assertEqual(
            self.client.get(reverse('admin:index')).status_code, 302
        )


class AnonimoTests(TestCase):
    """Sin cuenta no se llega a nada privado (RF-13)."""

    def test_las_paginas_privadas_redirigen_al_login(self):
        for url in (reverse('perfil'), reverse('consultas'),
                    reverse('consulta_nueva'), reverse('soporte'),
                    reverse('panel'), reverse('panel_tramites')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn(reverse('login'), r['Location'])

    def test_las_paginas_publicas_son_publicas(self):
        for url in (reverse('inicio'), reverse('tramites'),
                    reverse('chatbot'), reverse('password_reset')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_no_hay_nadie_registrado(self):
        self.assertEqual(User.objects.count(), 0)
