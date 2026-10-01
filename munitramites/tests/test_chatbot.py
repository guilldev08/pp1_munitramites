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
from types import SimpleNamespace
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

from .base import CHATBOT_LLM_APAGADO, TestCase, ciudadano, tramite


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

    def test_un_saludo_con_pregunta_no_tapa_la_pregunta(self):
        """«hola, ¿qué necesito…?» tenía que buscar, no saludar igual."""
        tramite()

        rta = responder('hola, ¿qué necesito para renovar el DNI?')

        self.assertNotIn('Soy el asistente', rta['texto'])
        self.assertTrue(rta['tramites'])
        self.assertEqual(rta['tramites'][0].titulo, 'Renovacion de DNI')

    def test_agradecer_y_despedirse_tienen_su_respuesta(self):
        self.assertIn('De nada', responder('¡gracias!')['texto'])
        self.assertIn('Hasta luego', responder('chau')['texto'])

    def test_un_seguimiento_corto_se_busca_con_lo_preguntado_antes(self):
        tramite()

        # Solo: no hay términos con qué puntuar → no se inventa nada.
        self.assertEqual(responder('¿y eso?')['tramites'], [])

        # Con la charla previa: el seguimiento se ancla al trámite del
        # que venían hablando.
        con_historia = responder(
            '¿y eso?',
            [{'rol': 'usuario', 'texto': 'renovacion de DNI'}],
        )
        self.assertTrue(con_historia['tramites'])
        self.assertEqual(con_historia['tramites'][0].titulo,
                         'Renovacion de DNI')

    def test_es_limpieza_reconoce_la_orden(self):
        from munitramites.services.chatbot import es_limpieza

        self.assertTrue(es_limpieza('limpiar'))
        self.assertTrue(es_limpieza('¿Limpiar!'))
        self.assertFalse(es_limpieza('renovacion de DNI'))

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

    def test_el_boton_de_vaciar_no_se_muestra_sin_sesion(self):
        """Al anónimo no se le ofrece un botón que lo manda al login."""
        tramite()

        r = self.client.post(reverse('chatbot'), {'mensaje': 'renovacion de DNI'})
        self.assertNotContains(r, 'Vaciar chat')

        self.client.force_login(ciudadano(username='ana'))
        r = self.client.get(reverse('chatbot'))
        self.assertContains(r, 'Vaciar chat')

    def test_escribir_limpiar_vacia_la_charla(self):
        """La ayuda promete «limpiar» escrito a mano: tiene que funcionar."""
        tramite()
        self.client.post(reverse('chatbot_api'),
                         {'mensaje': 'renovacion de DNI'})
        self.client.post(reverse('chatbot_api'), {'mensaje': 'limpiar'})

        historial = self.client.get(reverse('chatbot_api')).json()['historial']

        # Se fue la charla anterior; quedan la orden del usuario y la
        # confirmación del asistente.
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0]['texto'], 'limpiar')
        self.assertEqual(historial[1]['rol'], 'bot')
        self.assertIn('vaciamos', historial[1]['texto'])
        self.assertNotIn('Renovacion de DNI',
                         [m['texto'] for m in historial])

    def test_la_vista_pasa_la_charla_anterior_al_pipeline(self):
        """El historial llega a `responder`: sin eso no hay conversación."""
        tramite()

        with mock.patch(
            'munitramites.views.chatbot.responder',
            return_value={'texto': 'ok', 'tramites': [], 'fragmentos': []},
        ) as r:
            self.client.post(reverse('chatbot'),
                             {'mensaje': 'renovacion de DNI'})
            self.client.post(reverse('chatbot'), {'mensaje': '¿y eso?'})

        pregunta, historial = r.call_args.args
        self.assertEqual(pregunta, '¿y eso?')
        self.assertEqual(historial[0]['texto'], 'renovacion de DNI')


class BuscadorTests(TestCase):
    """La barra de búsqueda del sitio también dispara el asistente."""

    def test_la_barra_de_busqueda_ofrece_al_asistente(self):
        """Con texto en «Buscar» aparece el panel de respuesta + fallback."""
        tramite()

        r = self.client.get(reverse('tramites'), {'q': 'renovacion de DNI'})

        self.assertContains(r, 'id="respuesta-ia"')
        self.assertContains(r, 'data-consulta="renovacion de DNI"')
        # Sin JavaScript: enlace al chat con la misma consulta
        self.assertContains(r, reverse('chatbot') + '?q=')

        # El panel vive en el parcial compartido: anda en la portada también
        r_portada = self.client.get(reverse('inicio'),
                                    {'q': 'renovacion de DNI'})
        self.assertContains(r_portada, 'id="respuesta-ia"')

    def test_sin_texto_en_la_barra_no_aparece_el_panel(self):
        tramite()

        r = self.client.get(reverse('tramites'))

        self.assertNotContains(r, 'id="respuesta-ia"')

    def test_el_enlace_sin_javascript_de_verdad_responde(self):
        tramite()

        r = self.client.get(reverse('chatbot'), {'q': 'renovacion de DNI'})

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Renovacion de DNI')

    def test_el_json_del_buscador_responde_sin_guardar_la_charla(self):
        tramite()

        r = self.client.get(reverse('buscador_api'),
                            {'q': 'renovacion de DNI'})

        datos = r.json()
        self.assertTrue(datos['texto'])
        self.assertEqual(datos['tramites'][0]['titulo'], 'Renovacion de DNI')
        self.assertIn('url', datos['tramites'][0])
        # Privacidad: lo que se busca en la barra NO queda en la charla
        self.assertEqual(self.client.session.get('chatbot', []), [])

    def test_el_buscador_usa_el_mismo_pipeline_sin_historial(self):
        with mock.patch(
            'munitramites.views.chatbot.responder',
            return_value={'texto': 'ok', 'tramites': [], 'fragmentos': []},
        ) as r:
            self.client.get(reverse('buscador_api'), {'q': '¿y el plazo?'})

        # Misma función que el chat, pero cada búsqueda se resuelve sola
        r.assert_called_once_with('¿y el plazo?')

    def test_el_json_sin_consulta_no_llama_al_pipeline(self):
        with mock.patch('munitramites.views.chatbot.responder') as r:
            resp = self.client.get(reverse('buscador_api'))

        self.assertEqual(resp.json(), {'texto': '', 'tramites': []})
        r.assert_not_called()


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
        # Con temperature 0,2 el modelo redactaba SIEMPRE la misma frase
        # de apertura; hace falta temperatura para que varíe.
        self.assertEqual(post.call_args.args[1]['temperature'], 0.6)

    def test_la_pregunta_previa_se_manda_al_modelo(self):
        """Sin el hilo el modelo no sabe de qué habla «¿y el plazo?»."""
        tramite()
        historial = [
            {'rol': 'usuario', 'texto': 'renovacion de DNI'},
            {'rol': 'bot', 'texto': 'Se renueva con el DNI anterior.'},
        ]

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', return_value=MODELO_RESPONDE
            ) as post:
                responder('¿y el plazo?', historial)

        mensajes = post.call_args.args[1]['messages']
        # Sólo la PREGUNTA anterior: las respuestas del propio asistente
        # no se mandan (el modelo las copiaba para otro trámite).
        self.assertEqual([m['role'] for m in mensajes],
                         ['system', 'user', 'user'])
        self.assertEqual(mensajes[1]['content'], 'renovacion de DNI')
        # La última siempre es la pregunta nueva, con el contexto RAG.
        self.assertIn('Contexto:', mensajes[-1]['content'])
        self.assertIn('¿y el plazo?', mensajes[-1]['content'])

    def test_a_una_pregunta_completa_no_se_le_manda_el_hilo(self):
        """El hilo es para interpretar seguimientos cortos; una consulta
        completa no lo necesita y con mensajes viejos el modelo se desvía."""
        tramite()
        historial = [
            {'rol': 'usuario', 'texto': 'renovacion de DNI'},
            {'rol': 'bot', 'texto': 'Se renueva con el DNI anterior.'},
        ]

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(
                LLMHttp, '_post', return_value=MODELO_RESPONDE
            ) as post:
                responder('que requisitos piden para los antecedentes penales',
                          historial)

        mensajes = post.call_args.args[1]['messages']
        self.assertEqual([m['role'] for m in mensajes], ['system', 'user'])

    def test_la_plantilla_local_no_se_repite_letra_por_letra(self):
        """Con una sola redacción, si el modelo caía todas las respuestas
        salían iguales: cada caso necesita más de una frase."""
        fragmentos = [SimpleNamespace(tramite_titulo='Renovacion de DNI')]
        plantilla = PlantillaLocal()

        textos = {
            plantilla.completar(f'consulta numero {i}', fragmentos)
            for i in range(12)
        }

        self.assertGreater(len(textos), 1)
        for texto in textos:
            self.assertIn('Encontré', texto)

    def test_la_plantilla_de_un_seguimiento_cita_los_tramites(self):
        """«¿y el plazo?» suelto no le dice nada al ciudadano: en vez de
        repetirlo se le citan los trámites que encontró."""
        fragmentos = [
            SimpleNamespace(tramite_titulo='Renovacion de DNI'),
            SimpleNamespace(tramite_titulo='Partida de Nacimiento'),
        ]

        texto = PlantillaLocal().completar(
            'y el plazo?', fragmentos,
            [{'rol': 'usuario', 'texto': 'renovacion de DNI'}],
        )

        self.assertIn('Encontré', texto)
        self.assertNotIn('y el plazo?', texto)
        self.assertIn('Renovacion de DNI', texto)

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


class AlucinacionesTests(TestCase):
    """«Manejo de alucinaciones» de punta a punta: lo que el prompt pide,
    lo chequea el código por si el modelo no obedece. Pasó en vivo con
    Qwen de 1,5B: contestó «la tasa es de 20 pesos» y «el plazo es de 30
    días hábiles», cifras que no estaban en ninguna parte de la base, y
    en dos turnos pegó el formato «Contexto: … Pregunta: …» de lleno."""

    def setUp(self):
        super().setUp()
        # El cooldown es estado del módulo: cada test arranca limpio.
        generacion._en_fallo_hasta = 0.0

    def tearDown(self):
        generacion._en_fallo_hasta = 0.0
        super().tearDown()

    def _con_texto(self, contenido, fragmentos):
        """`generar_respuesta` con el LLM devolviendo `contenido`.

        La pregunta no es por un monto: así no se cruza con el
        pre-chequeo de montos y el test llega al filtro que le interesa.
        """
        respuesta = {'choices': [{'message': {'content': contenido}}]}
        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(LLMHttp, '_post', return_value=respuesta):
                return generacion.generar_respuesta('que requisitos piden',
                                                    fragmentos)

    @staticmethod
    def _fragmento(texto, titulo='Renovacion de DNI'):
        return SimpleNamespace(tramite_titulo=titulo, texto=texto)

    def test_se_descarta_una_cifra_que_no_esta_en_el_contexto(self):
        fragmentos = [self._fragmento(
            'Renovacion de DNI. Requisitos: DNI anterior y formulario.'
        )]

        texto = self._con_texto(
            'La tasa por renovar el DNI es de 20 pesos.', fragmentos
        )

        # Cayó en la plantilla, que sólo repite datos del índice.
        self.assertIn('Encontré', texto)
        self.assertNotIn('20', texto)

    def test_las_cifras_que_vienen_del_contexto_se_aceptan(self):
        fragmentos = [self._fragmento(
            'Presentar el formulario 2 veces y esperar 10 dias.'
        )]

        texto = self._con_texto(
            'Hay que presentarlo 2 veces y esperar 10 dias.', fragmentos
        )

        self.assertEqual(texto,
                         'Hay que presentarlo 2 veces y esperar 10 dias.')

    def test_los_numeros_de_lista_no_se_toman_por_inventados(self):
        fragmentos = [self._fragmento(
            'Renovacion de DNI. Requisitos: DNI y formulario.'
        )]

        texto = self._con_texto(
            'Presentar: 1. DNI vigente. 2. Formulario.', fragmentos
        )

        self.assertEqual(texto, 'Presentar: 1. DNI vigente. 2. Formulario.')

    def test_el_filtro_tambien_actua_en_el_camino_de_las_vistas(self):
        tramite()   # contexto de prueba, sin montos ni plazos
        respuesta = {'choices': [{'message': {
            'content': 'Renovar el DNI cuesta 20 pesos.',
        }}]}

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(LLMHttp, '_post', return_value=respuesta):
                rta = responder('renovacion de DNI')

        self.assertIn('Encontré', rta['texto'])

    def test_un_monto_no_indexado_se_contesta_sin_llamar_al_modelo(self):
        """Si el contexto no trae montos, la única respuesta posible del
        modelo sería inventada: ni se le pregunta (pasó en vivo, respondió
        «$50.000.000» por renovar el DNI)."""
        fragmentos = [self._fragmento(
            'Renovacion de DNI. Requisitos: DNI anterior y abonar la tasa.'
        )]

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(LLMHttp, '_post') as post:
                texto = generacion.generar_respuesta('cuanto se paga por el DNI',
                                                     fragmentos)

        self.assertEqual(post.call_count, 0)   # ni gastó los segundos de CPU
        self.assertIn('No dispongo', texto)
        self.assertIn('monto', texto)

    def test_si_el_contexto_trae_el_monto_se_le_pregunta_al_modelo(self):
        fragmentos = [self._fragmento('Renovacion de DNI. Tasa: $5.000.')]
        respuesta = {'choices': [{'message': {
            'content': 'La tasa es de $5.000.',
        }}]}

        with self.settings(CHATBOT_LLM=OLLAMA_DE_PRUEBA):
            with mock.patch.object(LLMHttp, '_post',
                                   return_value=respuesta) as post:
                texto = generacion.generar_respuesta('cuanto se paga por el DNI',
                                                     fragmentos)

        self.assertEqual(post.call_count, 1)
        self.assertEqual(texto, 'La tasa es de $5.000.')

    def test_se_corta_el_eco_del_prompt(self):
        eco = (
            'Contexto:\n• Renovacion de DNI.\n\n'
            'Pregunta: donde se hace la partida de nacimiento\n'
            'Se hace en el Registro Civil.'
        )

        self.assertEqual(
            generacion._sin_eco(eco, 'donde se hace la partida de nacimiento'),
            'Se hace en el Registro Civil.',
        )

    def test_si_del_eco_no_queda_respuesta_vacia(self):
        eco = 'Contexto:\n• Renovacion de DNI.\n\nPregunta: renovacion de DNI'

        self.assertEqual(generacion._sin_eco(eco, 'renovacion de DNI'), '')

    def test_una_respuesta_normal_pasa_sin_tocar(self):
        texto = 'Según el trámite, se presenta en la ventanilla del registro.'
        self.assertEqual(generacion._sin_eco(texto, 'renovacion de DNI'),
                         texto)
