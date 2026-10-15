"""Cliente del modelo de lenguaje: Gemma 4 corriendo en Ollama.

Ollama se instala en la PC (fuera del contenedor) y expone una API REST
en el puerto 11434. Desde el contenedor se lo alcanza por
`host.docker.internal`, que Docker Desktop resuelve a la máquina
anfitriona. La única dependencia es `requests`, que ya está en el
proyecto: ni SDK ni claves (Ollama local no pide ninguna).

El contrato con el pipeline es UNA función: `redactar(pregunta,
fragmentos, historial)`. Si el modelo no está configurado, no responde,
se cae o devuelve basura, devuelve None — y la etapa 3 cae en la
plantilla local. El asistente nunca se queda mudo por un modelo.

Cuando Ollama se cae, se anota el momento del fallo y por
`COOLDOWN_FALLO` segundos no se vuelve a intentar: sin eso, cada
mensaje de la charla sumaría el timeout completo de la conexión
muerta en la cara del ciudadano.
"""

import re
import time

import requests
from django.conf import settings

__all__ = ['activo', 'redactar']

# Gemma 4 piensa antes de contestar: aunque Ollama arma el template, a
# veces el bloque de «thought» o los tokens de control se cuelan en el
# contenido. Se barren antes de devolver: son marcas, no prosa.
_LIMPIEZA = (
    re.compile(r'<\|channel>thought\n.*?<channel\|>', re.DOTALL),
    re.compile(r'<\|[^|<>]{1,24}\|>'),
    re.compile(r'<channel\|>'),
)

# Segundos sin reintentar tras un fallo (ver docstring).
COOLDOWN_FALLO = 60

# Momento (monotónico) del último fallo; 0.0 = nunca falló.
_ultimo_fallo = 0.0

# Gemma 4 con la configuración que recomienda Google para todos los
# casos de uso (temperatura 1.0, top_p 0.95, top_k 64). `num_predict`
# acorta la respuesta: el asistente contesta máximo 4 oraciones.
OPCIONES = {
    'temperature': 1.0,
    'top_p': 0.95,
    'top_k': 64,
    'num_predict': 220,
    'num_ctx': 4096,
}

# El system prompt va en español porque es el idioma del asistente:
# Gemma 4 soporta `system` nativo y Ollama arma el template por nosotros.
_SYSTEM = (
    'Sos el asistente de trámites de Munitramites, de la Provincia de '
    'Misiones (Argentina). Contestás en español rioplatense, con vos. '
    'Reglas estrictas:\n'
    '- Respondé SOLO con la información del CONTEXTO de abajo: es tu '
    'única fuente válida.\n'
    '- Nunca inventes montos, plazos, requisitos ni horarios. Si un dato '
    'no está en el contexto, no existe para vos.\n'
    '- Si el contexto no alcanza para contestar, decí que no dispongás '
    'de ese dato y recomendá abrir la ficha del trámite o sus enlaces '
    'oficiales.\n'
    '- Mencioná los trámites por su nombre exacto y cerrá indicando que '
    'la ficha tiene los requisitos y los enlaces oficiales.\n'
    '- Máximo 4 oraciones. Sin presentaciones ni despedidas.'
)


def activo():
    """¿El asistente debe redactar con el LLM (y hay a dónde pegarle)?"""
    return settings.CHATBOT_LLM == 'ollama'


def _url(ruta):
    return f'{settings.OLLAMA_URL.rstrip("/")}/{ruta.lstrip("/")}'


def _armar_user(pregunta, fragmentos, historial):
    """El pedido al modelo: contexto del índice + charla + pregunta.

    El CONTEXTO es lo único que el modelo tiene permitido usar, así que
    va primero y con los títulos de los trámites para que pueda citar
    las fuentes por su nombre exacto.
    """
    partes = ['CONTEXTO (fichas de trámites de la base):']
    for f in fragmentos:
        partes.append(f'- {f.tramite_titulo}: {f.texto}')

    previos = [
        m for m in (historial or [])
        if str(m.get('texto') or '').strip()
    ][-6:]
    if previos:
        partes.append('CHARLA PREVIA:')
        for m in previos:
            rol = 'El ciudadano' if m.get('rol') == 'usuario' else 'Vos'
            partes.append(f'{rol}: {m["texto"]}')

    partes.append(f'PREGUNTA DEL CIUDADANO: {pregunta}')
    return '\n'.join(partes)


def redactar(pregunta, fragmentos, historial=()):
    """La respuesta del modelo, o None si no hay modelo disponible.

    `fragmentos` son los Fragmento recuperados por el RAG (etapa 2) y
    `historial` la charla de la sesión, para seguir el hilo en
    seguimientos cortos («¿y el plazo?»).
    """
    global _ultimo_fallo

    if not activo():
        return None
    if time.monotonic() - _ultimo_fallo < COOLDOWN_FALLO:
        return None

    try:
        respuesta = requests.post(
            _url('/api/chat'),
            json={
                'model': settings.OLLAMA_MODELO,
                'messages': [
                    {'role': 'system', 'content': _SYSTEM},
                    {
                        'role': 'user',
                        'content': _armar_user(
                            pregunta, fragmentos, historial,
                        ),
                    },
                ],
                'stream': False,
                # Gemma 4 piensa antes de contestar: en CPU ese modo se
                # come los tokens y deja la respuesta vacía. Apagado,
                # la respuesta sale entera y más rápido.
                'think': False,
                'options': OPCIONES,
            },
            timeout=settings.OLLAMA_TIMEOUT,
        )
        respuesta.raise_for_status()
        texto = (
            (respuesta.json().get('message') or {}).get('content') or ''
        ).strip()
    except (requests.RequestException, ValueError):
        # Ollama caído, timeout o respuesta ilegible: se anota el fallo
        # y la etapa 3 usa la plantilla local.
        _ultimo_fallo = time.monotonic()
        return None

    if not texto:
        _ultimo_fallo = time.monotonic()
        return None
    for patron in _LIMPIEZA:
        texto = patron.sub('', texto)
    return texto.strip() or None
