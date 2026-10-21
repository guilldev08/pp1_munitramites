"""Pruebas del asistente con LLM (Groq, simulado).

El modelo NUNCA se toca de verdad en los tests: se simula la API de
Groq con mocks y se reactiva `CHATBOT_LLM` con override_settings
(settings.py lo apaga en los tests). Lo que se prueba acá es el
contrato entre el pipeline y el modelo: que redacte con contexto, que
charle libre cuando NO hay contexto, que caiga en la plantilla si el
modelo no está, y que un fallo no se pague en cada mensaje.
"""

from unittest.mock import MagicMock, patch

import requests
from django.test import override_settings

from munitramites.services.chatbot import llm
from munitramites.services.chatbot.pipeline import responder

from .base import TestCase, tramite


def _respuesta_modelo(texto):
    """Mock del JSON que devuelve Groq en /openai/v1/chat/completions."""
    respuesta = MagicMock()
    respuesta.json.return_value = {
        'choices': [{'message': {'role': 'assistant', 'content': texto}}],
    }
    return respuesta


def _apagar_cooldown():
    llm._ultimo_fallo = 0.0


@override_settings(
    CHATBOT_LLM='groq',
    GROQ_API_KEY='gsk_prueba',
    GROQ_MODELO='openai/gpt-oss-120b',
    GROQ_TIMEOUT=5,
)
class LlmTests(TestCase):
    """Con CHATBOT_LLM='groq': Groq redacta; si no puede, plantilla."""

    def setUp(self):
        super().setUp()
        _apagar_cooldown()
        self.addCleanup(_apagar_cooldown)
        tramite()  # «Renovacion de DNI» activo, para que el RAG encuentre

    def test_el_llm_redacta_la_respuesta(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            return_value=_respuesta_modelo(
                'Renovás el DNI con el DNI anterior en vigor.'
            ),
        ) as post:
            rta = responder('¿qué necesito para renovar el DNI?')

        self.assertEqual(
            rta['texto'],
            'Renovás el DNI con el DNI anterior en vigor.',
        )
        self.assertEqual(len(rta['tramites']), 1)  # las fuentes no cambian

        # El pedido va a la API de Groq, con la clave y el modelo.
        self.assertEqual(
            post.call_args.args[0],
            'https://api.groq.com/openai/v1/chat/completions',
        )
        self.assertEqual(
            post.call_args.kwargs['headers']['Authorization'],
            'Bearer gsk_prueba',
        )
        cuerpo = post.call_args.kwargs['json']
        self.assertEqual(cuerpo['model'], 'openai/gpt-oss-120b')
        mensajes = cuerpo['messages']
        self.assertEqual(mensajes[0]['role'], 'system')
        self.assertIn('rioplatense', mensajes[0]['content'])
        self.assertIn('CONTEXTO', mensajes[1]['content'])
        self.assertIn('Renovacion de DNI', mensajes[1]['content'])
        self.assertIn('¿qué necesito para renovar el DNI?',
                      mensajes[1]['content'])

    @override_settings(GROQ_API_KEY='')
    def test_sin_clave_no_se_llama_a_groq(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
        ) as post:
            rta = responder('¿qué necesito para renovar el DNI?')

        # Sin clave, el asistente responde con la plantilla y no toca
        # la red: es el estado en que queda clonado el repo.
        self.assertTrue(rta['texto'].startswith('Encontré'))
        post.assert_not_called()

    def test_si_groq_se_cae_vuelve_a_la_plantilla(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            side_effect=requests.ConnectionError('sin groq'),
        ):
            rta = responder('¿qué necesito para renovar el DNI?')

        # La plantilla local empieza con «Encontré» (resiliencia).
        self.assertTrue(rta['texto'].startswith('Encontré'))
        self.assertEqual(len(rta['tramites']), 1)

    def test_tras_un_fallo_no_se_reintenta_en_cada_mensaje(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            side_effect=requests.ConnectionError('sin groq'),
        ) as post:
            responder('¿qué necesito para renovar el DNI?')
            responder('¿y con la partida de nacimiento?')

        # Un solo intento: el cooldown cubre el segundo mensaje.
        self.assertEqual(post.call_count, 1)

    def test_respuesta_vacia_del_modelo_cae_en_plantilla(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            return_value=_respuesta_modelo('   '),
        ):
            rta = responder('¿qué necesito para renovar el DNI?')

        self.assertTrue(rta['texto'].startswith('Encontré'))

    def test_sin_contexto_el_llm_charla_libre(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            return_value=_respuesta_modelo(
                'Munitramites es el portal de trámites de Misiones: '
                'buscá por tema o preguntame por un trámite.'
            ),
        ) as post:
            rta = responder('¿qué es Munitramites?')

        # No es la frase pregrabada «no encontré nada»: contesta el
        # modelo y no cita trámites (no hay).
        self.assertEqual(
            rta['texto'],
            'Munitramites es el portal de trámites de Misiones: '
            'buscá por tema o preguntame por un trámite.',
        )
        self.assertEqual(rta['tramites'], [])

        # Se le avisa explícitamente que NO hay contexto, para que
        # pueda charlar pero no se invente fichas.
        cuerpo = post.call_args.kwargs['json']
        self.assertIn('sin resultados',
                      cuerpo['messages'][1]['content'])
        self.assertIn('¿qué es Munitramites?',
                      cuerpo['messages'][1]['content'])

    def test_con_llm_la_pregunta_de_monto_llega_al_modelo(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
            return_value=_respuesta_modelo(
                'Ese monto no figura en la base: revisá la ficha '
                'oficial del trámite.'
            ),
        ) as post:
            rta = responder('¿cuánto cuesta el trámite de renovación '
                            'del DNI?')

        # Con modelo, la prohibición de inventar cifras vive en el
        # prompt (y el modelo cita el contexto si el monto está ahí):
        # el corte determinista recién corre cuando no hay modelo.
        self.assertIn('no figura en la base', rta['texto'])
        post.assert_called_once()


@override_settings(CHATBOT_LLM='')
class SinLlmTests(TestCase):
    """Sin CHATBOT_LLM: la plantilla local de toda la vida, sin red."""

    def setUp(self):
        super().setUp()
        _apagar_cooldown()
        tramite()

    def test_se_usa_la_plantilla_y_no_se_llama_a_ningun_modelo(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
        ) as post:
            rta = responder('¿qué necesito para renovar el DNI?')

        self.assertTrue(rta['texto'].startswith('Encontré'))
        post.assert_not_called()

    def test_sin_llm_el_corte_de_montos_sigue_determinista(self):
        with patch(
            'munitramites.services.chatbot.llm.requests.post',
        ) as post:
            rta = responder('¿cuánto cuesta el trámite de renovación '
                            'del DNI?')

        # Sin modelo no se puede confiar en un prompt: el «no dispongo
        # de MONTO» sale determinista, sin siquiera intentar red.
        self.assertIn('No dispongo', rta['texto'])
        self.assertIn('monto', rta['texto'])
        post.assert_not_called()
