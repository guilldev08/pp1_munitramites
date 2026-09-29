"""ESP-02 / RF-03, RF-07, RF-11, RF-13 — Roles y permisos.

El documento define dos roles: **Usuario** (ciudadano) y **Administrador**.
En Django ese rol se materializa con `is_staff` (y con los grupos, si
hiciera falta un tercer rol): quien no lo tiene no llega a las funciones
de gestión.

Criterio de aceptación: «Los usuarios solo pueden acceder a las funciones
permitidas según su rol».
"""

from django.contrib.auth.models import User

from django.urls import reverse

from munitramites.models import Organismo, Tramite

from .base import TestCase, administrador, ciudadano, municipio, organismo


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


class AdministradorTests(TestCase):
    """Permisos del rol Administrador."""

    def setUp(self):
        self.admin = administrador()
        self.client.force_login(self.admin)

    def test_entra_al_panel(self):
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_ve_las_tablas_del_sistema(self):
        """RF-12: usuarios, trámites, consultas, organismos, perfiles…"""
        r = self.client.get(reverse('admin:index'))

        for ruta in ('/admin/munitramites/tramite/',
                     '/admin/munitramites/consulta/',
                     '/admin/munitramites/organismo/',
                     '/admin/munitramites/perfil/',
                     '/admin/auth/user/'):
            self.assertContains(r, ruta)

    def test_puede_gestionar_usuarios(self):
        """RF-11: consultar y administrar los usuarios registrados."""
        ciudadano(username='ana')

        r = self.client.get(reverse('admin:auth_user_changelist'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ana')

    def test_puede_gestionar_tramites(self):
        """RF-07: crear y editar trámites desde el panel."""
        r = self.client.post(reverse('admin:munitramites_tramite_add'), {
            'titulo': 'Certificado de residencia',
            'tema': 'Documentacion',
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

    def test_puede_cargar_un_organismo_con_su_area_de_accion(self):
        r = self.client.post(reverse('admin:munitramites_organismo_add'), {
            'nombre': 'Direccion de Catastro',
            'direccion': 'Calle San Martin 321',
            'ocupacion': 'Bienes raices',
        })

        self.assertEqual(r.status_code, 302)
        self.assertTrue(Organismo.objects.filter(
            nombre='Direccion de Catastro', ocupacion='Bienes raices'
        ).exists())


class AnonimoTests(TestCase):
    """Sin cuenta no se llega a nada privado (RF-13)."""

    def test_las_paginas_privadas_redirigen_al_login(self):
        for url in (reverse('perfil'), reverse('consultas'),
                    reverse('consulta_nueva'), reverse('soporte')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn(reverse('login'), r['Location'])

    def test_las_paginas_publicas_son_publicas(self):
        for url in (reverse('inicio'), reverse('tramites'),
                    reverse('chatbot'), reverse('password_reset')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_no_hay_nadie_registrado(self):
        self.assertEqual(User.objects.count(), 0)
