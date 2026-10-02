"""Funcionalidades con IA / Chatbot (RAG) — «Asistente Virtual Inteligente».

Criterios de aceptación del documento:

    Precisión contextual ..... responde solo con la información indexada
    Manejo de alucinaciones .. si no sabe, lo dice en lugar de inventar
    Cita de fuentes .......... siempre enlaza el trámite del que habla
    Privacidad ............... no almacena el historial de forma permanente

La etapa 3 (generar) redacta con la plantilla local, anclada a los
fragmentos: no hay red que simular, así que acá se prueba el
comportamiento del asistente.
"""


from types import SimpleNamespace
from unittest import mock

from django.urls import reverse

from munitramites.models import Consulta, Tramite
from munitramites.services.chatbot import generacion, responder
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
