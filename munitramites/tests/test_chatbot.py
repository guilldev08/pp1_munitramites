"""Funcionalidades con IA / Chatbot (RAG) — «Asistente Virtual Inteligente».

Criterios de aceptación del documento:

    Precisión contextual ..... responde solo con la información indexada
    Manejo de alucinaciones .. si no sabe, lo dice en lugar de inventar
    Cita de fuentes .......... siempre enlaza el trámite del que habla
    Privacidad ............... no almacena el historial de forma permanente

La etapa 3 (generar) anda con Qwen vía Ollama; en los tests la red se
simula, así que acá se prueba el cableado, no la calidad del modelo.
"""


import http.client
import urllib.error
from unittest import mock

from django.conf import settings
from django.urls import reverse

from munitramites.models import Consulta, Tramite
from munitramites.services.chatbot import generacion, responder
from munitramites.services.chatbot.generacion import (
    INSTRUCCION,
    LLMHttp,
    PlantillaLocal,
    proveedor,
)

from .base import CHATBOT_LLM_APAGADO, TestCase, tramite


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


# Configuración idéntica a la de settings.CHATBOT_LLM (Qwen en Ollama),
# pero apuntando a una URL que nunca se usa: la red se mockea igual.
OLLAMA_DE_PRUEBA = {
    'proveedor': 'ollama',
    'api_key': '',
    'modelo': 'qwen2.5:1.5b',
    'base_url': 'http://ollama:11434/v1',
    'timeout': 5,
}

# Lo que devolvería Ollama si el modelo contestara.
MODELO_RESPONDE = {
    'choices': [{
        'message': {
            'content': ('Con el DNI en vigor y el formulario completado '
                        'ya podés renovarlo en el Registro Civil.'),
        },
    }],
}


class PruebaDelLLMTests(TestCase):
    """Etapa 3 con el modelo de verdad (Qwen corriendo en Ollama).

    Los tests no esperan a la PC que genere tokens: se simula la respuesta
    HTTP para chequear el cableado (URL, claves, prompt y caída a la
    plantilla si algo falla).
    """

    def setUp(self):
        super().setUp()
        # El cooldown es estado del módulo: cada test arranca limpio.
        generacion._en_fallo_hasta = 0.0

    def tearDown(self):
        generacion._en_fallo_hasta = 0.0
        super().tearDown()

    def test_sin_configuracion_responde_la_plantilla_local(self):
        with self.settings(CHATBOT_LLM=CHATBOT_LLM_APAGADO):
            p = proveedor()
        self.assertIsInstance(p, PlantillaLocal)

    def test_ollama_queda_configurado_aunque_no_haya_clave(self):
        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            p = proveedor()

        self.assertIsInstance(p, LLMHttp)
        self.assertTrue(p.esta_configurado())

    def test_ollama_sin_url_no_esta_configurado(self):
        with self.settings(CHATBOT_LLM={**OLLAMA_DE_PRUEBA, 'base_url': ''}):
            p = proveedor()
        self.assertIsInstance(p, PlantillaLocal)

    def test_llama_al_end_point_de_ollama_sin_autorizacion(self):
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', return_value=MODELO_RESPONDE
            ) as post:
                rta = responder('renovacion de DNI')

        url, payload, encabezados = post.call_args.args
        self.assertEqual(url, 'http://ollama:11434/v1/chat/completions')
        # Ollama no pide clave: no se manda Authorization.
        self.assertEqual(encabezados, {})
        self.assertEqual(payload['model'], 'qwen2.5:1.5b')
        self.assertEqual(rta['texto'],
                         MODELO_RESPONDE['choices'][0]['message']['content'])

    def test_el_prompt_le_ordena_responder_solo_con_el_contexto(self):
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', return_value=MODELO_RESPONDE
            ) as post:
                responder('renovacion de DNI')

        mensajes = post.call_args.args[1]['messages']
        self.assertEqual(mensajes[0]['role'], 'system')
        self.assertEqual(mensajes[0]['content'], INSTRUCCION)
        self.assertEqual(mensajes[1]['role'], 'user')
        # El contexto que recibe el modelo es el RAG: los fragmentos
        # recuperados (TOP_K como máximo), no la base entera.
        self.assertIn('Renovacion de DNI', mensajes[1]['content'])
        self.assertLessEqual(
            mensajes[1]['content'].count('•'), settings.CHATBOT_TOP_K
        )
        self.assertEqual(post.call_args.args[1]['max_tokens'], 256)

    def test_si_el_llm_falla_vuelve_la_plantilla_local(self):
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post',
                side_effect=urllib.error.URLError('contenedor apagado'),
            ):
                rta = responder('renovacion de DNI')

        # Nada de «no pude conectar» para el ciudadano: la plantilla.
        self.assertTrue(rta['texto'])
        self.assertIn('Encontré', rta['texto'])
        self.assertTrue(rta['tramites'])

    def test_timeout_o_respuesta_caida_tambien_vuelven_a_la_plantilla(self):
        """El modelo tarda más que `timeout` o la conexión se corta a mitad."""
        tramite()

        for fallo in (TimeoutError('se pasó del tiempo'),
                      http.client.RemoteDisconnected('se cortó la respuesta')):
            with self.subTest(fallo=type(fallo).__name__):
                with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
                    with mock.patch.object(LLMHttp, '_post', side_effect=fallo):
                        rta = responder('renovacion de DNI')

                self.assertIn('Encontré', rta['texto'])

    def test_tras_un_fallo_no_insiste_con_la_red(self):
        """Sin cooldown, cada consulta pagaría ~4 s de DNS para nada."""
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', side_effect=OSError('contenedor caído')
            ) as post:
                rta1 = responder('renovacion de DNI')
                rta2 = responder('renovacion de DNI')

        self.assertEqual(post.call_count, 1)
        # Aunque no insista con la red, el ciudadano siempre recibe texto.
        self.assertIn('Encontré', rta1['texto'])
        self.assertIn('Encontré', rta2['texto'])

    def test_pasado_el_cooldown_vuelve_a_intentar(self):
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', side_effect=OSError('caído')
            ) as post:
                responder('renovacion de DNI')
                self.assertEqual(post.call_count, 1)

                # Se cumple el plazo (60 s): vuelve a tocar la red.
                generacion._en_fallo_hasta = 0.0
                responder('renovacion de DNI')
                self.assertEqual(post.call_count, 2)

    def test_una_respuesta_ok_no_deja_cooldown(self):
        tramite()

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', return_value=MODELO_RESPONDE
            ) as post:
                responder('renovacion de DNI')
                responder('renovacion de DNI')

        self.assertEqual(post.call_count, 2)
        self.assertEqual(generacion._en_fallo_hasta, 0.0)
