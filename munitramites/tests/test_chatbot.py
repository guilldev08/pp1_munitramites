"""Funcionalidades con IA / Chatbot (RAG) — «Asistente Virtual Inteligente».

Criterios de aceptación del documento:

    Precisión contextual ..... responde solo con la información indexada
    Manejo de alucinaciones .. si no sabe, lo dice en lugar de inventar
    Cita de fuentes .......... siempre enlaza el trámite del que habla
    Privacidad ............... no almacena el historial de forma permanente
"""


from django.urls import reverse

from munitramites.models import Consulta, Tramite
from munitramites.services.chatbot import responder

from .base import TestCase, tramite


class PipelineTests(TestCase):
    """Pruebas directas del servicio (sin pasar por HTTP)."""

    def test_encuentra_el_tramite_y_cita_la_fuente(self):
        tramite()

        rta = responder('¿qué necesito para renovar el DNI?')

        self.assertTrue(rta['tramites'])
        self.assertEqual(rta['tramites'][0].titulo, 'Renovacion de DNI')
        self.assertTrue(rta['texto'])
        self.assertTrue(rta['fragmentos'])

    def test_no_inventar_respuesta_sin_contexto(self):
        tramite()

        rta = responder('¿cuánto cuesta un helado de mochaccino?')

        self.assertIn('No dispongo', rta['texto'])
        self.assertEqual(rta['tramites'], [])
        self.assertEqual(rta['fragmentos'], [])

    def test_pregunta_vacia_pide_que_escriba(self):
        rta = responder('   ')
        self.assertIn('Escribí', rta['texto'])

    def test_saludo_y_ayuda(self):
        self.assertIn('Hola', responder('hola')['texto'])
        self.assertIn('buscar', responder('ayuda')['texto'])

    def test_busca_por_requisito(self):
        tramite()  # «DNI en vigor y formulario completado»

        rta = responder('¿qué piden para la licencia de conducir?')
        # Aunque no haya licencias, tiene que responder algo coherente
        self.assertTrue(rta['texto'])

    def test_desaparece_si_se_desactiva_el_tramite(self):
        t = tramite()
        rta = responder('renovacion de DNI')
        self.assertTrue(rta['tramites'])

        t.activo = False
        t.save()

        rta = responder('renovacion de DNI')
        self.assertEqual(rta['tramites'], [])


class VistasChatbotTests(TestCase):

    def test_el_modal_pregunta_por_json(self):
        tramite()

        r = self.client.post(reverse('chatbot_api'),
                             {'mensaje': 'renovacion de DNI'})

        historial = r.json()['historial']
        self.assertEqual(r.status_code, 200)
        self.assertEqual(historial[-1]['rol'], 'bot')
        self.assertEqual(historial[-1]['tramites'][0]['titulo'],
                         'Renovacion de DNI')
        # La vista agrega la URL para que JS no tenga que armarla
        self.assertEqual(historial[-1]['tramites'][0]['url'],
                         reverse('tramite_detalle', args=[Tramite.objects.first().pk]))

    def test_el_historial_se_repite_en_las_siguientes_consultas(self):
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        r = self.client.get(reverse('chatbot_api'))

        self.assertEqual(len(r.json()['historial']), 2)

    def test_vaciar_la_charla(self):
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        self.client.post(reverse('chatbot_api'), {'accion': 'limpiar'})

        r = self.client.get(reverse('chatbot_api'))
        self.assertEqual(r.json()['historial'], [])

    def test_pagina_del_chat_sin_javascript(self):
        tramite()

        r = self.client.post(reverse('chatbot'), {'mensaje': 'renovacion de DNI'})

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Renovacion de DNI')

    def test_boton_de_vaciar_pide_sesion(self):
        """La charla es privada: vaciarla exige estar identificado."""
        r = self.client.post(reverse('chatbot_limpiar'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])


class PrivacidadTests(TestCase):
    """«Sin almacenar el historial conversacional de forma permanente»."""

    def test_la_charla_no_se_guarda_en_la_base(self):
        tramite()
        consultas_antes = Consulta.objects.count()
        tramites_antes = Tramite.objects.count()

        for pregunta in ('renovacion de DNI', 'partida de nacimiento'):
            self.client.post(reverse('chatbot_api'), {'mensaje': pregunta})

        self.assertEqual(Consulta.objects.count(), consultas_antes)
        self.assertEqual(Tramite.objects.count(), tramites_antes)

    def test_la_charla_se_pierde_al_cerrar_el_navegador(self):
        tramite()
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        self.assertIn('chatbot', self.client.session)

        # Nueva sesión (como si el navegador se cerrara)
        self.client.cookies.clear()
        r = self.client.get(reverse('chatbot_api'))

        self.assertEqual(r.json()['historial'], [])
