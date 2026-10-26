"""Funcionalidades con IA / Chatbot (RAG) — «Asistente Virtual Inteligente».

Criterios de aceptación del documento:

    Precisión contextual ..... responde solo con la información indexada
    Manejo de alucinaciones .. si no sabe, lo dice en lugar de inventar
    Cita de fuentes .......... siempre enlaza el trámite del que habla
    Historial ................ cada usuario tiene sus conversaciones guardadas
    Privacidad ............... cada usuario solo puede abrir sus conversaciones

La etapa 3 (generar) redacta con la plantilla local, anclada a los
fragmentos: no hay red que simular, así que acá se prueba el
comportamiento del asistente.
"""


from types import SimpleNamespace
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from munitramites.models import (
    ConversacionChat, Direccion, FuenteMensaje, Tramite,
)
from munitramites.services.chatbot import generacion, indexar, llm, responder
from munitramites.services.chatbot.generacion import PlantillaLocal

from .base import TestCase, ciudadano, tramite


class PipelineTests(TestCase):
    """Pruebas directas del servicio (sin pasar por HTTP)."""

    def test_encuentra_el_tramite_y_cita_la_fuente(self):
        tramite()

        rta = responder('¿qué necesito para renovar el DNI?')

        self.assertTrue(rta['tramites'])
        self.assertEqual(rta['tramites'][0].titulo, 'Renovacion de DNI')
        self.assertTrue(rta['texto'])
        self.assertTrue(rta['fragmentos'])

    def test_el_indice_incluye_las_direcciones(self):
        t = tramite()
        Direccion.objects.create(
            tramite=t, lugar='Sede Costanera', municipio=t.municipio,
            direccion='Av. Costanera 500',
        )

        indexar.invalidar()
        ficha = next(
            f for f in indexar.obtener_indice() if f.tipo == 'ficha'
        )

        self.assertIn('Sede Costanera', ficha.texto)
        self.assertIn('Av. Costanera 500', ficha.texto)

    def test_el_indice_usa_la_direccion_del_organismo_como_respaldo(self):
        t = tramite()

        indexar.invalidar()
        ficha = next(
            f for f in indexar.obtener_indice() if f.tipo == 'ficha'
        )

        self.assertIn(t.organismo.direccion, ficha.texto)

    def test_no_inventar_respuesta_sin_contexto(self):
        tramite()

        rta = responder('¿cuánto cuesta un helado de mochaccino?')

        # Cita lo que se preguntó: eso hace que dos consultas nunca
        # reciban exactamente el mismo texto.
        self.assertIn('helado de mochaccino', rta['texto'])
        self.assertEqual(rta['tramites'], [])
        self.assertEqual(rta['fragmentos'], [])

    def test_dos_consultas_sin_resultados_no_se_contesta_lo_mismo(self):
        """Pasó en vivo: «g» y «ag» recibían la MISMA frase fija."""
        self.assertNotEqual(responder('g')['texto'],
                            responder('ag')['texto'])

    def test_una_consulta_de_dos_letras_pide_que_la_completen(self):
        """«No encontré nada sobre "g"» no le sirve a nadie."""
        texto = responder('ag')['texto']

        self.assertIn('«ag»', texto)
        self.assertIn('completa', texto)

    def test_la_misma_consulta_se_contesta_igual(self):
        """Estable: la misma pregunta no cambia de respuesta en la charla."""
        self.assertEqual(responder('g')['texto'], responder('g')['texto'])

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
        self.client.force_login(ciudadano(username='ana'))

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

    def test_la_respuesta_enlaza_dentro_del_texto(self):
        tramite()
        self.client.force_login(ciudadano(username='ana'))

        r = self.client.post(reverse('chatbot_api'),
                             {'mensaje': 'renovacion de DNI'})
        respuesta = r.json()['historial'][-1]

        # El texto no trae una sección de fuentes ni URLs: el enlace va
        # en la primera aparición del título, dentro de la respuesta.
        self.assertNotIn('Fuente:', respuesta['texto'])
        self.assertNotIn('http', respuesta['texto'])
        enlaces = [s for s in respuesta['segmentos'] if s['url']]
        self.assertEqual(len(enlaces), 1)
        self.assertEqual(enlaces[0]['texto'], 'Renovacion de DNI')
        self.assertEqual(enlaces[0]['url'], respuesta['tramites'][0]['url'])
        self.assertEqual(
            ''.join(s['texto'] for s in respuesta['segmentos']),
            respuesta['texto'],
        )

    def test_el_historial_se_repite_en_las_siguientes_consultas(self):
        self.client.force_login(ciudadano(username='ana'))
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        r = self.client.get(reverse('chatbot_api'))

        self.assertEqual(len(r.json()['historial']), 2)

    def test_la_api_ya_no_acepta_la_accion_limpiar(self):
        self.client.force_login(ciudadano(username='ana'))
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})

        r = self.client.post(reverse('chatbot_api'), {'accion': 'limpiar'})

        self.assertEqual(r.status_code, 400)
        historial = self.client.get(reverse('chatbot_api')).json()['historial']
        self.assertEqual(len(historial), 2)

    def test_la_pagina_vieja_del_chat_ya_no_existe(self):
        self.assertEqual(self.client.get('/chatbot/').status_code, 404)
        self.assertEqual(
            self.client.post('/chatbot/limpiar/').status_code, 404
        )

    def test_sin_sesion_el_json_de_la_charla_devuelve_403(self):
        """El JavaScript del modal intercepta el 403 y abre el de login."""
        r = self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})

        self.assertEqual(r.status_code, 403)
        self.assertIn('error', r.json())

    def test_el_modal_tiene_hamburguesa_y_lista_de_chats(self):
        self.client.force_login(ciudadano(username='ana'))

        r = self.client.get(reverse('tramites'))

        self.assertContains(r, 'id="chat-hamburguesa"')
        self.assertContains(r, 'id="chat-lista"')
        self.assertContains(r, 'id="chat-nuevo"')
        self.assertNotContains(r, 'chat-limpiar')
        self.assertNotContains(r, 'Vaciar')

    def test_escribir_limpiar_vacia_la_charla(self):
        """La ayuda promete «limpiar» escrito a mano: tiene que funcionar."""
        tramite()
        self.client.force_login(ciudadano(username='ana'))
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
            self.client.force_login(ciudadano(username='ana'))
            self.client.post(reverse('chatbot_api'),
                             {'mensaje': 'renovacion de DNI'})
            self.client.post(reverse('chatbot_api'), {'mensaje': '¿y eso?'})

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
        # El panel enlaza al modal del asistente con la misma consulta.
        self.assertContains(r, 'data-abrir="modal-chat"')
        self.assertContains(r, 'data-chat-pregunta="renovacion de DNI"')

        # El panel vive en el parcial compartido, pero la landing no lo
        # repite: el listado vive solo en /tramites/
        r_landing = self.client.get(reverse('inicio'),
                                    {'q': 'renovacion de DNI'})
        self.assertNotContains(r_landing, 'id="respuesta-ia"')

    def test_sin_texto_en_la_barra_no_aparece_el_panel(self):
        tramite()

        r = self.client.get(reverse('tramites'))

        self.assertNotContains(r, 'id="respuesta-ia"')

    def test_el_json_del_buscador_responde_sin_guardar_la_charla(self):
        tramite()
        self.client.force_login(ciudadano(username='ana'))

        r = self.client.get(reverse('buscador_api'),
                            {'q': 'renovacion de DNI'})

        datos = r.json()
        self.assertTrue(datos['texto'])
        self.assertEqual(datos['tramites'][0]['titulo'], 'Renovacion de DNI')
        self.assertIn('url', datos['tramites'][0])
        # Privacidad: lo que se busca en la barra NO queda en la charla
        self.assertEqual(
            ConversacionChat.objects.filter(
                usuario__username='ana'
            ).count(),
            0,
        )

    def test_el_buscador_usa_el_mismo_pipeline_sin_historial(self):
        with mock.patch(
            'munitramites.views.chatbot.responder',
            return_value={'texto': 'ok', 'tramites': [], 'fragmentos': []},
        ) as r:
            self.client.get(reverse('buscador_api'), {'q': '¿y el plazo?'})

        # Misma función que el chat, pero cada búsqueda se resuelve sola
        r.assert_called_once_with('¿y el plazo?', usar_llm=False)

    @override_settings(CHATBOT_LLM='groq', GROQ_API_KEY='gsk_prueba')
    def test_el_buscador_publico_no_gasta_la_api(self):
        """Sin sesión, la barra responde con plantillas y no llama a Groq."""
        tramite()
        llm._ultimo_fallo = 0.0

        with mock.patch(
            'munitramites.services.chatbot.llm.groq.requests.post',
        ) as post:
            r = self.client.get(reverse('buscador_api'),
                                {'q': 'renovacion de DNI'})

        self.assertTrue(r.json()['texto'])
        post.assert_not_called()

    @override_settings(CHATBOT_LLM='groq', GROQ_API_KEY='gsk_prueba')
    def test_el_buscador_con_sesion_usa_el_modelo(self):
        """Con sesión, la barra sí redacta con Groq (y no guarda charla)."""
        tramite()
        self.client.force_login(ciudadano(username='ana'))
        llm._ultimo_fallo = 0.0

        respuesta = mock.MagicMock()
        respuesta.json.return_value = {
            'choices': [{'message': {'content': 'Respuesta de prueba.'}}],
        }
        with mock.patch(
            'munitramites.services.chatbot.llm.groq.requests.post',
            return_value=respuesta,
        ) as post:
            r = self.client.get(reverse('buscador_api'),
                                {'q': 'renovacion de DNI'})

        self.assertEqual(r.json()['texto'], 'Respuesta de prueba.')
        post.assert_called_once()
        self.assertEqual(
            ConversacionChat.objects.filter(
                usuario__username='ana'
            ).count(),
            0,
        )

    def test_el_json_sin_consulta_no_llama_al_pipeline(self):
        with mock.patch('munitramites.views.chatbot.responder') as r:
            resp = self.client.get(reverse('buscador_api'))

        self.assertEqual(
            resp.json(),
            {'texto': '', 'tramites': [], 'segmentos': []},
        )
        r.assert_not_called()


class HistorialPersistenteTests(TestCase):
    """El historial queda en Firebird, separado por usuario."""

    def setUp(self):
        self.user = ciudadano(username='ana')
        self.client.force_login(self.user)
        tramite()

    def test_la_charla_persiste_al_cerrar_el_navegador(self):
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        self.assertNotIn('chatbot', self.client.session)

        # Otra sesión del mismo usuario, como si abriera otro navegador.
        self.client.cookies.clear()
        self.client.force_login(self.user)
        r = self.client.get(reverse('chatbot_api'))

        self.assertEqual(len(r.json()['historial']), 2)
        self.assertEqual(r.json()['historial'][0]['texto'], 'hola')

    def test_cada_usuario_ve_solo_sus_conversaciones(self):
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})

        otro = ciudadano(username='beto')
        otro_cliente = self.client_class()
        otro_cliente.force_login(otro)
        r = otro_cliente.get(reverse('chatbot_api'))

        self.assertEqual(r.json()['historial'], [])
        self.assertEqual(r.json()['conversaciones'], [])

    def test_se_puede_crear_otra_conversacion_y_volver_a_la_anterior(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )
        primera = r.json()['conversacion']['id']

        r = self.client.post(reverse('chatbot_api'), {'accion': 'nueva'})
        segunda = r.json()['conversacion']['id']
        self.assertNotEqual(primera, segunda)
        self.assertEqual(r.json()['historial'], [])

        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        r = self.client.get(
            reverse('chatbot_api'), {'conversacion': primera}
        )
        self.assertEqual(r.json()['conversacion']['id'], primera)
        self.assertEqual(len(r.json()['historial']), 2)

    def test_la_respuesta_cita_la_ficha_interna(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )
        datos = r.json()
        conversacion = datos['conversacion']['id']
        respuesta = datos['historial'][1]

        self.assertEqual(respuesta['rol'], 'bot')
        self.assertTrue(respuesta['tramites'])
        fuente = respuesta['tramites'][0]
        self.assertEqual(fuente['titulo'], 'Renovacion de DNI')
        self.assertEqual(
            fuente['url'],
            reverse('tramite_detalle', args=[fuente['pk']]),
        )
        # El modelo no arma enlaces: el texto queda limpio y el servidor
        # enlaza el título del trámite dentro de la respuesta.
        self.assertNotIn('http', respuesta['texto'])
        self.assertNotIn('Fuente:', respuesta['texto'])
        enlaces = [s for s in respuesta['segmentos'] if s['url']]
        self.assertTrue(enlaces)
        self.assertEqual(enlaces[0]['texto'], 'Renovacion de DNI')
        self.assertEqual(enlaces[0]['url'], fuente['url'])
        self.assertEqual(
            ''.join(s['texto'] for s in respuesta['segmentos']),
            respuesta['texto'],
        )
        self.assertEqual(
            FuenteMensaje.objects.filter(
                mensaje__conversacion_id=conversacion
            ).count(),
            len(respuesta['tramites']),
        )

    def test_no_se_puede_abrir_la_conversacion_de_otro_usuario(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'mi documento secreto'}
        )
        primera = r.json()['conversacion']['id']

        otro = ciudadano(username='beto')
        otro_cliente = self.client_class()
        otro_cliente.force_login(otro)

        r = otro_cliente.get(
            reverse('chatbot_api'), {'conversacion': primera}
        )
        self.assertIsNone(r.json()['conversacion'])
        self.assertEqual(r.json()['historial'], [])

        # Aunque mande el id ajeno, el POST crea SU conversación.
        r = otro_cliente.post(
            reverse('chatbot_api'),
            {'mensaje': 'hola', 'conversacion': primera},
        )
        self.assertNotEqual(r.json()['conversacion']['id'], primera)

        # La conversación de ana quedó intacta.
        r = self.client.get(
            reverse('chatbot_api'), {'conversacion': primera}
        )
        self.assertEqual(len(r.json()['historial']), 2)

    def test_la_lista_muestra_la_conversacion_elegida(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )
        primera = r.json()['conversacion']['id']

        r = self.client.post(reverse('chatbot_api'), {'accion': 'nueva'})
        self.assertNotEqual(r.json()['conversacion']['id'], primera)
        self.client.post(
            reverse('chatbot_api'), {'mensaje': 'partida de nacimiento'}
        )

        r = self.client.get(reverse('chatbot_api'), {'conversacion': primera})
        datos = r.json()

        self.assertEqual(datos['conversacion']['id'], primera)
        self.assertEqual(len(datos['conversaciones']), 2)
        textos = [m['texto'] for m in datos['historial']]
        self.assertIn('renovacion de DNI', textos)
        self.assertNotIn('partida de nacimiento', textos)

    def test_seleccionar_cambia_la_conversacion_activa(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )
        primera = r.json()['conversacion']['id']

        self.client.post(reverse('chatbot_api'), {'accion': 'nueva'})
        self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})

        r = self.client.post(
            reverse('chatbot_api'),
            {'accion': 'seleccionar', 'conversacion': primera},
        )
        self.assertEqual(r.json()['conversacion']['id'], primera)

        # El mensaje siguiente se guarda en la conversación elegida.
        r = self.client.post(reverse('chatbot_api'), {'mensaje': 'gracias'})
        self.assertEqual(r.json()['conversacion']['id'], primera)
        self.assertEqual(len(r.json()['historial']), 4)

    def test_el_titulo_sale_de_la_primera_pregunta(self):
        r = self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )
        self.assertEqual(r.json()['conversacion']['titulo'], 'renovacion de DNI')

    def test_la_lista_trae_todas_las_conversaciones(self):
        """La barra lateral no se corta en 50: lista el historial completo."""
        for i in range(60):
            ConversacionChat.objects.create(
                usuario=self.user, titulo=f'Chat {i}'
            )

        r = self.client.get(reverse('chatbot_api'))
        datos = r.json()

        self.assertEqual(len(datos['conversaciones']), 60)
        self.assertIn('actualizado', datos['conversaciones'][0])

    def test_limpiar_escrito_solo_borra_la_conversacion_activa(self):
        r = self.client.post(reverse('chatbot_api'), {'mensaje': 'hola'})
        primera = r.json()['conversacion']['id']

        r = self.client.post(reverse('chatbot_api'), {'accion': 'nueva'})
        segunda = r.json()['conversacion']['id']
        self.client.post(
            reverse('chatbot_api'), {'mensaje': 'renovacion de DNI'}
        )

        self.client.post(reverse('chatbot_api'), {'mensaje': 'limpiar'})

        r = self.client.get(reverse('chatbot_api'), {'conversacion': segunda})
        historial = r.json()['historial']
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0]['texto'], 'limpiar')
        self.assertEqual(historial[1]['rol'], 'bot')
        self.assertNotIn('Renovacion de DNI',
                         [m['texto'] for m in historial])

        # La primera conversación sigue intacta.
        r = self.client.get(reverse('chatbot_api'), {'conversacion': primera})
        self.assertEqual(len(r.json()['historial']), 2)
        self.assertEqual(len(r.json()['conversaciones']), 2)


class PlantillaLocalTests(TestCase):
    """La redacción de la etapa 3: variantes estables, sin repetirse."""

    def test_la_plantilla_local_no_se_repite_letra_por_letra(self):
        """Con una sola redacción, TODAS las respuestas salían iguales:
        cada caso necesita más de una frase."""
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


class AlucinacionesTests(TestCase):
    """«Manejo de alucinaciones» de punta a punta: el asistente nunca
    inventa un dato que no esté indexado. Las preguntas por MONTO se
    cortan antes de redactar: si la cifra no está en el contexto, la
    única respuesta posible sería una invención (pasó en vivo con
    «$50.000.000» por renovar el DNI)."""

    @staticmethod
    def _fragmento(texto, titulo='Renovacion de DNI'):
        return SimpleNamespace(tramite_titulo=titulo, texto=texto)

    def test_un_monto_no_indexado_se_contesta_sin_inventar(self):
        fragmentos = [self._fragmento(
            'Renovacion de DNI. Requisitos: DNI anterior y abonar la tasa.'
        )]

        texto = generacion.generar_respuesta('cuanto se paga por el DNI',
                                             fragmentos)

        self.assertIn('No dispongo', texto)
        self.assertIn('monto', texto)

    def test_dos_preguntas_de_monto_no_reciben_el_mismo_texto(self):
        """La respuesta por monto era UNA frase fija: ahora cita lo que
        se preguntó, así dos consultas distintas no salen idénticas."""
        fragmentos = [self._fragmento(
            'Renovacion de DNI. Requisitos: DNI anterior y abonar la tasa.'
        )]

        a = generacion.generar_respuesta(
            'cuanto se paga por el DNI', fragmentos)
        b = generacion.generar_respuesta(
            'cuanto vale la habilitacion', fragmentos)

        self.assertNotEqual(a, b)
        self.assertIn('«cuanto se paga por el DNI»', a)
        self.assertIn('«cuanto vale la habilitacion»', b)

    def test_si_el_contexto_trae_el_monto_se_responde_normal(self):
        """El corte sólo salta cuando el monto NO está: si la ficha lo
        trae, la respuesta sale de la plantilla como cualquier otra."""
        fragmentos = [self._fragmento('Renovacion de DNI. Tasa: $5.000.')]

        texto = generacion.generar_respuesta('cuanto se paga por el DNI',
                                             fragmentos)

        self.assertIn('Encontré', texto)
