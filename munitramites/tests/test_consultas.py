"""ESP-05 / RF-08, RF-09, RF-10 — Consultas, sugerencias y soporte.

Criterios: «El formulario permite enviar la información y esta queda
registrada correctamente» y «El administrador debe poder visualizar y
gestionar las consultas y sugerencias recibidas».
"""


from django.urls import reverse

from munitramites.models import Consulta
from munitramites.views import PREFIJO_SOPORTE

from .base import TestCase, administrador, ciudadano, tramite


class EnviarConsultasTests(TestCase):

    def setUp(self):
        self.user = ciudadano(username='ana')
        self.client.force_login(self.user)

    def test_envia_consulta(self):
        """RF-08."""
        r = self.client.post(reverse('consulta_nueva'), {
            'tipo': 'consulta',
            'tramite': '',
            'asunto': 'Horarios del Registro Civil',
            'contenido': '¿Atienden los sabados por la mañana?',
        })

        self.assertRedirects(r, reverse('consultas'))
        consulta = Consulta.objects.get()
        self.assertEqual(consulta.usuario, self.user)
        self.assertEqual(consulta.estado, 'pendiente')

    def test_envia_sugerencia(self):
        """RF-09."""
        r = self.client.post(reverse('consulta_nueva'), {
            'tipo': 'sugerencia',
            'tramite': '',
            'asunto': 'Sugerencia de horarios',
            'contenido': 'Podrian publicar los horarios en la portada.',
        })

        self.assertRedirects(r, reverse('consultas'))
        self.assertEqual(Consulta.objects.get().tipo, 'sugerencia')

    def test_puede_asociarla_a_un_tramite(self):
        t = tramite()

        self.client.post(reverse('consulta_nueva'), {
            'tipo': 'consulta', 'tramite': t.pk,
            'asunto': 'Duda sobre el DNI',
            'contenido': '¿Cuanto tarda el tramite?',
        })

        self.assertEqual(Consulta.objects.get().tramite, t)

    def test_no_envia_contenido_vacio(self):
        r = self.client.post(reverse('consulta_nueva'), {
            'tipo': 'consulta', 'tramite': '',
            'asunto': 'Sin contenido', 'contenido': '',
        })

        self.assertEqual(r.status_code, 200)
        self.assertEqual(Consulta.objects.count(), 0)

    def test_preselecciona_el_tramite_de_la_ficha(self):
        t = tramite()
        r = self.client.get(reverse('consulta_nueva'), {'tramite': t.pk})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(str(r.context['form'].initial['tramite']), str(t.pk))


class VerConsultasTests(TestCase):

    def test_cada_uno_solo_ve_las_suyas(self):
        """RF-13: control de acceso por usuario."""
        ana = ciudadano(username='ana')
        ajena = Consulta.objects.create(
            usuario=ciudadano(username='otra'),
            asunto='Consulta de Otra', contenido='Otro contenido.',
        )

        self.client.force_login(ana)
        Consulta.objects.create(
            usuario=ana, asunto='Consulta de Ana',
            contenido='Contenido de la consulta.',
        )
        r = self.client.get(reverse('consultas'))

        self.assertContains(r, 'Consulta de Ana')
        self.assertNotContains(r, 'Consulta de Otra')

        # El detalle de la ajena no se puede ver
        r = self.client.get(reverse('consulta_detalle', args=[ajena.pk]))
        self.assertRedirects(r, reverse('consultas'))


class SoporteTests(TestCase):

    def test_pide_sesion(self):
        r = self.client.get(reverse('soporte'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])

    def test_guarda_el_pedido_como_consulta(self):
        user = ciudadano(username='ana')
        self.client.force_login(user)

        r = self.client.post(reverse('soporte'), {
            'asunto': 'No puedo abrir una ficha',
            'mensaje': 'Al abrir el tramite me aparece un error raro.',
        })

        self.assertRedirects(r, reverse('soporte'))
        pedido = Consulta.objects.get(asunto__startswith=PREFIJO_SOPORTE)
        self.assertEqual(pedido.usuario, user)
        self.assertIn('No puedo abrir', pedido.asunto)

    def test_lista_los_pedidos_del_usuario(self):
        user = ciudadano(username='ana')
        Consulta.objects.create(
            usuario=user, asunto=f'{PREFIJO_SOPORTE}Problema con el chat',
            contenido='El chat no me responde.',
        )
        self.client.force_login(user)

        r = self.client.get(reverse('soporte'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Problema con el chat')


class GestionDelAdminTests(TestCase):
    """RF-10: el administrador visualiza, responde y cierra consultas."""

    def setUp(self):
        self.ciudadano = ciudadano(username='ana')
        self.consulta = Consulta.objects.create(
            usuario=self.ciudadano, asunto='Duda de Ana',
            contenido='¿Que documentos necesito?',
        )
        self.admin = administrador()

    def test_el_admin_ve_todas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('consultas'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Duda de Ana')

    def test_el_admin_responde_y_cambia_el_estado(self):
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('consulta_detalle', args=[self.consulta.pk]),
            {'respuesta': 'Necesitás el DNI vigente y el formulario.'},
        )

        self.assertEqual(r.status_code, 302)
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.estado, 'respondido')
        self.assertIn('DNI vigente', self.consulta.respuesta)

    def test_el_ciudadano_no_puede_responder(self):
        self.client.force_login(self.ciudadano)

        self.client.post(
            reverse('consulta_detalle', args=[self.consulta.pk]),
            {'respuesta': 'Me respondo solo'},
        )

        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.estado, 'pendiente')
        self.assertEqual(self.consulta.respuesta, '')

    def test_el_ciudadano_ve_la_respuesta(self):
        self.consulta.estado = 'respondido'
        self.consulta.respuesta = 'Te respondemos hoy.'
        self.consulta.save()

        self.client.force_login(self.ciudadano)
        r = self.client.get(reverse('consulta_detalle', args=[self.consulta.pk]))

        self.assertContains(r, 'Te respondemos hoy.')
