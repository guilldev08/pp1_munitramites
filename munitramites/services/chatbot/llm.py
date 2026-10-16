"""Cliente del modelo de lenguaje: Gemma 4 corriendo en Ollama.

Ollama es un servicio MÁS del docker-compose (imagen `ollama/ollama`,
volumen `ollama_data` con los modelos): el proyecto es autocontenido y
se levanta en cualquier PC con `docker compose up`, sin instalar nada
aparte. Desde el servicio web se lo alcanza por `OLLAMA_URL`
(`http://ollama:11434`, la red interna del compose). Si algún día se
quiere usar el Ollama de la PC —por ejemplo, con GPU— alcanza con
apuntar `OLLAMA_URL` a `host.docker.internal:11434`. La única
dependencia del cliente es `requests`, que ya está en el proyecto: ni
SDK ni claves (Ollama local no pide ninguna).

El contrato con el pipeline es UNA función: `redactar(pregunta,
fragmentos, historial)`. Si el modelo no está configurado, no responde,
se cae o devuelve basura, devuelve None — y la etapa 3 cae en la
plantilla local. El asistente nunca se queda mudo por un modelo.

Se usa en DOS caminos: con contexto (la etapa 2 le pasó fragmentos) y
SIN contexto (la consulta no trajo ninguna ficha): en ese segundo caso
el modelo charla libre —saludos sueltos, «¿qué es este portal?»,
preguntas generales— pero con la misma prohibición de inventar datos
de trámites.

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
# acorta la respuesta: alcanza para las 8 oraciones que pide el
# prompt y corta cualquier divagación larga. `num_ctx` es 2048 y no
# 4096 a propósito: con la KV cache en q8_0 (ver docker-compose.yml)
# eso deja el pico de RAM del modelo por debajo del límite de la VM
# de Docker y 2048 sobra para contexto + historial corto.
OPCIONES = {
    'temperature': 1.0,
    'top_p': 0.95,
    'top_k': 64,
    'num_predict': 220,
    'num_ctx': 2048,
}

# El system prompt va en español porque es el idioma del asistente:
# Gemma 4 soporta `system` nativo y Ollama arma el template por
# nosotros. DOS NIVELES a propósito: los DATOS de trámites sólo del
# contexto (nunca inventar montos/plazos/requisitos), TODO LO DEMÁS en
# libre —ese es justamente el punto de meter un LLM: contestar en voz
# alta y no con frases pregrabadas.
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
    """¿El asistente debe redactar con el LLM (y hay a dónde pegarle)?"""
    return settings.CHATBOT_LLM == 'ollama'


def _url(ruta):
    return f'{settings.OLLAMA_URL.rstrip("/")}/{ruta.lstrip("/")}'


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
