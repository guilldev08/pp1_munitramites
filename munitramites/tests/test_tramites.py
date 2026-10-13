"""ESP-04, ESP-06, ESP-07 / RF-07, RF-12 — Trámites, filtros y ficha.

Criterios: «los datos se almacenan correctamente», «el usuario puede
navegar por las distintas secciones y utilizar los formularios sin errores»
y «el administrador puede consultar los trámites y actualizar su
información».
"""


from django.urls import reverse

from munitramites.models import Enlace, Requisito, Tema

from .base import TestCase, administrador, ciudadano, municipio, organismo, tramite


class LandingTests(TestCase):
    """La landing es la puerta de entrada: hero, dos botones y los pasos."""

    def test_es_publica_y_ofrece_las_dos_puertas(self):
        """ESP-07 — sin sesión: entrar o continuar sin cuenta."""
        r = self.client.get(reverse('inicio'))

        self.assertEqual(r.status_code, 200)
        # «Iniciar sesión» abre el modal de auth en la misma landing
        self.assertContains(
            r, 'data-abrir="modal-auth" data-tab="login">Iniciar sesión</a>')
        self.assertContains(r, 'Continuar sin sesión')
        self.assertContains(r, reverse('tramites'))
        self.assertContains(r, 'modal-chat')   # el asistente sigue al alcance

    def test_no_trae_ni_la_barra_del_chat_ni_el_listado(self):
        """La landing es liviana: la chatbar se retira y el listado vive
        recién en /tramites/."""
        tramite()

        r = self.client.get(reverse('inicio'))

        self.assertNotContains(r, 'barra-chat')
        self.assertNotContains(r, 'Renovacion de DNI')

    def test_muestra_los_tres_pasos_listos_para_aparecer(self):
        r = self.client.get(reverse('inicio'))

        self.assertContains(r, '¿Cómo funciona?')
        for paso in ('Buscá', 'Revisá los requisitos', 'Tramitá'):
            self.assertContains(r, paso)
        # la sección arranca oculta y aparece al hacer scroll (ver extra_js)
        self.assertContains(r, 'class="seccion revelar"')

    def test_al_logueado_le_cambia_los_botones(self):
        """Con sesión no se le vuelve a ofrecer entrar: va al listado."""
        self.client.force_login(ciudadano(username='ana'))

        r = self.client.get(reverse('inicio'))

        self.assertContains(r, '<a class="boton" href="%s">Ver trámites</a>'
                            % reverse('tramites'))
        self.assertNotContains(
            r, 'data-abrir="modal-auth" data-tab="login">Iniciar sesión</a>')

    def test_al_administrador_le_ofrece_el_panel(self):
        self.client.force_login(administrador())

        r = self.client.get(reverse('inicio'))

        self.assertContains(r, 'Ir al panel')
        self.assertContains(r, reverse('panel'))


class ListadoTests(TestCase):

    def test_lista_los_tramites_activos(self):
        tramite()
        tramite(titulo='Partida de nacimiento', tema='Documentación')

        r = self.client.get(reverse('tramites'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Renovacion de DNI')
        self.assertContains(r, 'Partida de nacimiento')

    def test_no_lista_los_inactivos(self):
        tramite(activo=False)

        r = self.client.get(reverse('tramites'))

        self.assertNotContains(r, 'Renovacion de DNI')

    def test_paga_de_a_seis_por_pagina(self):
        """RNF-03: el listado trae 6 por pantalla y el resto en la página 2."""
        for n in range(1, 8):
            tramite(titulo=f'Tramite numero {n}', tema='Documentación')

        r = self.client.get(reverse('tramites'))
        self.assertContains(r, 'Tramite numero 1')
        self.assertContains(r, 'Tramite numero 6')
        self.assertNotContains(r, 'Tramite numero 7')
        self.assertContains(r, 'pagina=2')

        r = self.client.get(reverse('tramites'), {'pagina': 2})
        self.assertContains(r, 'Tramite numero 7')
        self.assertNotContains(r, 'Tramite numero 1')

    def test_filtra_por_texto_tema_y_municipio(self):
        tramite()
        licencia = tramite(titulo='Licencia de conducir', tema='Tránsito',
                           municipio=municipio('Obera'))

        r = self.client.get(reverse('tramites'), {'q': 'licencia'})
        self.assertContains(r, 'Licencia de conducir')
        self.assertNotContains(r, 'Renovacion de DNI')

        r = self.client.get(reverse('tramites'),
                            {'tema': str(licencia.tema_id)})
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
    """RF-07: el administrador gestiona los trámites desde /panel/."""

    def test_el_admin_puede_editar_requisitos_y_enlaces(self):
        admin = administrador()
        t = tramite()

        self.client.force_login(admin)
        r = self.client.get(
            reverse('panel_tramite_editar', args=[t.pk])
        )

        self.assertEqual(r.status_code, 200)
        # Los inlines del panel: requisitos y enlaces oficiales
        self.assertContains(r, 'Requisitos')
        self.assertContains(r, 'Enlaces oficiales')

    def test_sin_staff_no_entra_al_panel(self):
        comun = ciudadano(username='comun')

        self.client.force_login(comun)
        r = self.client.get(reverse('panel'))

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('inicio'))
        # y el /admin/ de Django sigue respondiéndole con el login
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


class TemasTests(TestCase):
    """La tabla Tema: se carga desde el panel y alimenta los filtros."""

    def test_los_siete_temas_originales_vienen_cargados(self):
        """La migración siembra los temas que antes eran choices fijos."""
        nombres = set(Tema.objects.values_list('nombre', flat=True))

        self.assertTrue({
            'Documentación', 'Tránsito', 'Comercio', 'Seguridad',
            'Salud', 'Impuestos', 'Vivienda',
        } <= nombres)

    def test_un_tema_personalizado_se_muestra_en_la_lista(self):
        """RF-07: el admin carga un tema nuevo y la lista lo refleja."""
        tramite(titulo='Reciclaje urbano', tema='Medio Ambiente')

        r = self.client.get(reverse('tramites'))

        self.assertContains(r, 'etiqueta--tema">Medio Ambiente')

    def test_filtra_por_un_tema_personalizado(self):
        propio = tramite(titulo='Reciclaje urbano', tema='Medio Ambiente')
        tramite(titulo='Partida de nacimiento')

        r = self.client.get(reverse('tramites'), {'tema': str(propio.tema_id)})

        self.assertContains(r, 'Reciclaje urbano')
        self.assertNotContains(r, 'Partida de nacimiento')
