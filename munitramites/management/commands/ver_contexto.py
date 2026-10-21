"""Muestra la ventana de contexto que se manda a Groq, sin llamar a la API.

    docker compose exec web python manage.py ver_contexto "¿qué necesito para renovar el DNI?"

Imprime los fragmentos que recuperó el RAG, el system prompt y el
mensaje de usuario tal cual saldrían, y el tamaño del pedido
(caracteres y tokens estimados). No hace falta GROQ_API_KEY ni hay red:
sirve para revisar y ajustar el prompt con tranquilidad.

La ventana real que se manda en producción se arma en
`services/chatbot/llm/prompt.py`; `CHATBOT_TOP_K` (settings.py) decide
cuántos fragmentos entran (hoy 4).
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from ...services.chatbot import responder
from ...services.chatbot.llm.prompt import armar_mensajes


class Command(BaseCommand):
    help = (
        'Muestra el contexto exacto que se manda a Groq, sin llamar a la '
        'API.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'pregunta', nargs='+',
            help='Consulta a revisar, entre comillas.',
        )
        parser.add_argument(
            '--json', action='store_true',
            help='Volcar el payload `messages` como JSON.',
        )

    def handle(self, *args, **opciones):
        pregunta = ' '.join(opciones['pregunta']).strip()

        # usar_llm=False: usa el mismo pipeline (y los mismos fragmentos)
        # pero no toca la red.
        rta = responder(pregunta, usar_llm=False)
        fragmentos = rta['fragmentos']
        mensajes = armar_mensajes(pregunta, fragmentos)

        if opciones['json']:
            self.stdout.write(json.dumps(
                mensajes, ensure_ascii=False, indent=2,
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('Pregunta'))
        self.stdout.write(pregunta)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Fragmentos recuperados: {len(fragmentos)} '
            f'(máximo {settings.CHATBOT_TOP_K})'
        ))
        for fragmento in fragmentos:
            self.stdout.write(f'· {fragmento.tramite_titulo}')
            self.stdout.write(f'  {fragmento.texto}')

        if not fragmentos:
            self.stdout.write(self.style.WARNING(
                'Sin fragmentos: en producción NO se llama al modelo; '
                'responde la plantilla local.'
            ))

        total = 0
        for mensaje in mensajes:
            total += len(mensaje['content'])
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'[{mensaje["role"]}] {len(mensaje["content"])} caracteres'
            ))
            self.stdout.write(mensaje['content'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Total: {total} caracteres ≈ {total // 4} tokens (estimado). '
            'No se llamó a la API.'
        ))
