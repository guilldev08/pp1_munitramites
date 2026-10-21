"""Cliente del modelo de lenguaje: Groq (API compatible con OpenAI).

Groq corre los modelos en su infraestructura: el proyecto no baja ni
mantiene ningún modelo. El cliente es un POST a
`https://api.groq.com/openai/v1/chat/completions` con la clave
`GROQ_API_KEY`, que se pega en el `.env` de la raíz (nunca en el código
ni en el repo: `.env` está en `.gitignore`). La única dependencia es
`requests`, que ya está en el proyecto.

El contrato con el pipeline es UNA función: `redactar(pregunta,
fragmentos, historial)`. Si la clave no está configurada, el modelo no
responde, la API falla o devuelve basura, devuelve None — y la etapa 3
cae en la plantilla local. El asistente nunca se queda mudo por un
modelo.

Se usa en DOS caminos: con contexto (la etapa 2 le pasó fragmentos) y
SIN contexto (la consulta no trajo ninguna ficha): en ese segundo caso
el modelo charla libre —saludos sueltos, «¿qué es este portal?»,
preguntas generales— pero con la misma prohibición de inventar datos
de trámites.

Cuando Groq falla (clave vencida, cuota, red), se anota el momento del
fallo y por `COOLDOWN_FALLO` segundos no se vuelve a intentar: sin eso,
cada mensaje de la charla pagaría el timeout completo en la cara del
ciudadano.
"""

import time

import requests
from django.conf import settings

__all__ = ['activo', 'redactar']

# Segundos sin reintentar tras un fallo (ver docstring).
COOLDOWN_FALLO = 60

# Momento (monotónico) del último fallo; 0.0 = nunca falló.
_ultimo_fallo = 0.0

# Cómo se pide la respuesta: el prompt ya limita el largo a 1-8
# oraciones; `max_completion_tokens` es el tope de costo (en los modelos
# de razonamiento de Groq incluye el razonamiento interno).
TEMPERATURA = 0.7
MAX_TOKENS = 1200

# El system prompt va en español porque es el idioma del asistente.
# DOS NIVELES a propósito: los DATOS de trámites sólo del contexto
# (nunca inventar montos/plazos/requisitos), TODO LO DEMÁS en libre
# —ese es justamente el punto de meter un LLM: contestar en voz alta y
# no con frases pregrabadas.
_SYSTEM = (
    'Sos el asistente de Munitramites, un portal de trámites de la '
    'Provincia de Misiones (Argentina). Contestás en español '
    'rioplatense, con vos, cercano y natural, como un vecino que te '
    'ayuda en la ventanilla.\n'
    'Dos niveles:\n'
    '- DATOS DE TRÁMITES —requisitos, montos, plazos, horarios, '
    'organismos, dónde y cuándo se presenta— sólo pueden salir del '
    'CONTEXTO de abajo: es tu única fuente. Nunca los inventes. Si no '
    'están ahí, decí con tus palabras que en la base no figura y '
    'recomendá abrir la ficha o los enlaces oficiales.\n'
    '- TODO LO DEMÁS —saludos, charla, qué es este portal, cómo '
    'buscar, qué trámites suelen existir, dudas de cómo usarme— '
    'contestalo con libertad y buena onda, sin vueltas de '
    'formulario.\n'
    '- Si hay trámites en el CONTEXTO, mencionalos por su nombre '
    'exacto y señalá que la ficha trae los requisitos completos.\n'
    '- Si el CONTEXTO dice «sin resultados», no cites trámites '
    'inventados: contestá lo general y ofrecé ayudar a buscar de otra '
    'forma.\n'
    '- Natural: entre 1 y 8 oraciones según haga falta. Sin '
    'presentaciones ni despedidas.'
)


def activo():
    """¿Hay clave configurada y el asistente está encendido?"""
    return bool(settings.CHATBOT_LLM == 'groq' and settings.GROQ_API_KEY)


def _armar_user(pregunta, fragmentos, historial):
    """El pedido al modelo: contexto del índice + charla + pregunta.

    El CONTEXTO va primero y con los títulos de los trámites, para que
    el modelo pueda citar las fuentes por su nombre exacto. Sin
    fragmentos (consulta que no trajo fichas) se lo dice explícito:
    ahí el modelo puede charlar libre, pero sabe que no hay datos de
    trámites para citar y no debe inventar ninguno.
    """
    partes = ['CONTEXTO (fichas de trámites de la base):']
    if fragmentos:
        for f in fragmentos:
            partes.append(f'- {f.tramite_titulo}: {f.texto}')
    else:
        partes.append('(sin resultados: ninguna ficha responde a esto)')

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
    seguimientos cortos («¿y el plazo?»). `fragmentos` vacío es el
    camino de charla libre: el modelo contesta sin datos de trámites
    en pantalla, pero con las mismas reglas de no inventar.
    """
    global _ultimo_fallo

    if not activo():
        return None
    if time.monotonic() - _ultimo_fallo < COOLDOWN_FALLO:
        return None

    try:
        respuesta = requests.post(
            settings.GROQ_URL,
            headers={
                'Authorization': f'Bearer {settings.GROQ_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.GROQ_MODELO,
                'messages': [
                    {'role': 'system', 'content': _SYSTEM},
                    {
                        'role': 'user',
                        'content': _armar_user(
                            pregunta, fragmentos, historial,
                        ),
                    },
                ],
                'temperature': TEMPERATURA,
                'max_completion_tokens': MAX_TOKENS,
            },
            timeout=settings.GROQ_TIMEOUT,
        )
        respuesta.raise_for_status()
        opciones = respuesta.json().get('choices') or []
        texto = ''
        if opciones:
            texto = (
                (opciones[0].get('message') or {}).get('content') or ''
            ).strip()
    except (requests.RequestException, ValueError):
        # Sin red, timeout, 401 (clave vencida) o 429 (cuota):
        # se anota el fallo y la etapa 3 usa la plantilla local.
        _ultimo_fallo = time.monotonic()
        return None

    if not texto:
        _ultimo_fallo = time.monotonic()
        return None
    return texto
