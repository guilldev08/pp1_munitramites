"""Transporte HTTP: un POST a Groq (API compatible con OpenAI).

Este módulo solo sabe *cómo* se manda el pedido y *cómo* se lee la
respuesta. Quién y cuándo llama vive en `llm/__init__.py`; qué se manda
vive en `llm/prompt.py`. Así el día que cambie el proveedor se toca
solo este archivo.
"""

import requests
from django.conf import settings

# El prompt ya limita el largo a 1-8 oraciones; `max_completion_tokens`
# es el tope de costo (en los modelos de razonamiento de Groq incluye el
# razonamiento interno).
TEMPERATURA = 0.7
MAX_TOKENS = 1200


def pedir(mensajes):
    """Manda los mensajes a Groq y devuelve el texto (o '').

    Lanza las excepciones de `requests` y `ValueError` si la respuesta
    no es JSON: el llamador (`llm.redactar`) las convierte en None para
    que el pipeline use la plantilla local.
    """
    respuesta = requests.post(
        settings.GROQ_URL,
        headers={
            'Authorization': f'Bearer {settings.GROQ_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': settings.GROQ_MODELO,
            'messages': mensajes,
            'temperature': TEMPERATURA,
            'max_completion_tokens': MAX_TOKENS,
        },
        timeout=settings.GROQ_TIMEOUT,
    )
    respuesta.raise_for_status()

    opciones = respuesta.json().get('choices') or []
    if not opciones:
        return ''
    return (
        (opciones[0].get('message') or {}).get('content') or ''
    ).strip()
