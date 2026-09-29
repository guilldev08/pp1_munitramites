"""ESP-04, ESP-06, ESP-07 / RF-07, RF-12 — Trámites, filtros y ficha.

Criterios: «los datos se almacenan correctamente», «el usuario puede
navegar por las distintas secciones y utilizar los formularios sin errores»
y «el administrador puede consultar los trámites y actualizar su
información».
"""


from django.urls import reverse

from munitramites.models import Enlace, Requisito

from .base import TestCase, administrador, municipio, organismo, tramite


class PortadaTests(TestCase):

    def test_portada_es_publica_y_trae_la_barra_del_chat(self):
        """ESP-07: portada con la barra de ingreso del asistente."""
        tramite()

        r = self.client.get(reverse('inicio'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'barra-chat')
        self.assertContains(r, 'modal-auth')   # modal de login/registro
        self.assertContains(r, 'modal-chat')   # modal del chatbot
        self.assertContains(r, 'Renovacion de DNI')

    def test_portada_contiene_los_filtros(self):
        tramite(tema='Comercio', modalidad='virtual',
                titulo='Habilitacion comercial')

        r = self.client.get(reverse('inicio'), {'q': 'habilitacion'})

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Habilitacion comercial')
        self.assertNotContains(r, 'Renovacion de DNI')


class ListadoTests(TestCase):

    def test_lista_los_tramites_activos(self):
        tramite()
        tramite(titulo='Partida de nacimiento', tema='Documentacion')

        r = self.client.get(reverse('tramites'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Renovacion de DNI')
        self.assertContains(r, 'Partida de nacimiento')

    def test_no_lista_los_inactivos(self):
        tramite(activo=False)

        r = self.client.get(reverse('tramites'))

        self.assertNotContains(r, 'Renovacion de DNI')

    def test_filtra_por_texto_tema_y_municipio(self):
        tramite()
        tramite(titulo='Licencia de conducir', tema='Transito',
                municipio=municipio('Obera'))

        r = self.client.get(reverse('tramites'), {'q': 'licencia'})
        self.assertContains(r, 'Licencia de conducir')
        self.assertNotContains(r, 'Renovacion de DNI')

        r = self.client.get(reverse('tramites'), {'tema': 'Transito'})
        self.assertContains(r, 'Licencia de conducir')

        r = self.client.get(reverse('tramites'), {'municipio': municipio('Obera').pk})
        self.assertContains(r, 'Licencia de conducir')

    def test_busca_tambien_por_requisito(self):
        tramite()  # tiene «DNI en vigor y formulario completado»

        r = self.client.get(reverse('tramites'), {'q': 'formulario'})

        self.assertContains(r, 'Renovacion de DNI')

    def test_pagina_inexistente_no_rompe(self):
        tramite()
        r = self.client.get(reverse('tramites'), {'pagina': '99'})
        self.assertEqual(r.status_code, 200)


class FichaTests(TestCase):

    def test_ficha_completa(self):
        """ESP-07: descripción, requisitos, organismo y enlaces oficiales."""
        t = tramite()
        Enlace.objects.create(tramite=t, nombre='Pedir turno',
                              url='https://turnos.ejemplo.test/', orden=1)

        r = self.client.get(reverse('tramite_detalle', args=[t.pk]))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Renovacion de DNI')
        self.assertContains(r, 'DNI en vigor y formulario completado')
        self.assertContains(r, 'Registro Civil de Misiones')
        # El botón usa el nombre que cargó el admin (RF de enlaces)
        self.assertContains(r, 'Pedir turno')
        self.assertContains(r, 'https://turnos.ejemplo.test/')

    def test_un_tramite_inactivo_no_se_muestra(self):
        t = tramite(activo=False)
        r = self.client.get(reverse('tramite_detalle', args=[t.pk]))
        self.assertEqual(r.status_code, 404)

    def test_ficha_inexistente_da_404(self):
        r = self.client.get(reverse('tramite_detalle', args=[99999]))
        self.assertEqual(r.status_code, 404)

    def test_sin_enlaces_no_muestra_el_panel(self):
        t = tramite()
        r = self.client.get(reverse('tramite_detalle', args=[t.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Enlaces oficiales')

    def test_requisitos_se_borran_con_el_tramite(self):
        t = tramite()
        self.assertEqual(Requisito.objects.filter(tramite=t).count(), 1)
        t.delete()
        self.assertEqual(Requisito.objects.filter(tramite=t.pk).count(), 0)


class AdminTramitesTests(TestCase):
    """RF-07: el administrador gestiona los trámites."""

    def test_el_admin_puede_editar_requisitos_y_enlaces(self):
        admin = administrador()
        t = tramite()

        self.client.force_login(admin)
        r = self.client.get(
            reverse('admin:munitramites_tramite_change', args=[t.pk])
        )

        self.assertEqual(r.status_code, 200)
        # Los inlines del admin: requisitos y enlaces oficiales
        self.assertContains(r, 'Requisito')
        self.assertContains(r, 'Enlace oficial')

    def test_sin_staff_no_entra_al_panel(self):
        ciudadano = administrador(username='comun')
        ciudadano.is_staff = False
        ciudadano.save()

        self.client.force_login(ciudadano)
        r = self.client.get(reverse('admin:index'))

        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])


class ApiTests(TestCase):

    def test_devuelve_json_de_los_activos(self):
        tramite()

        r = self.client.get(reverse('api_tramites'))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['count'], 1)
        self.assertEqual(r.json()['tramites'][0]['titulo'], 'Renovacion de DNI')
