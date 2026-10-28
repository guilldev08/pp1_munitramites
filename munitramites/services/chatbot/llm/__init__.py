"""El modelo de lenguaje del asistente: Groq.

Groq corre los modelos en su infraestructura: el proyecto no baja ni
mantiene ningún modelo. El paquete está partido en tres, para que cada
cosa se pueda revisar sola:

    prompt.py   la ventana de contexto (system + user) que se manda
    groq.py     el POST a la API compatible con OpenAI
    __init__.py cuándo se llama: activo(), cooldown y fallback

La clave `GROQ_API_KEY` se pega en el `.env` de la raíz (nunca en el
código ni en el repo: `.env` está en `.gitignore`). La única dependencia
es `requests`, que ya está en el proyecto.

El contrato con el pipeline es UNA función: `redactar(pregunta,
fragmentos, historial)`. Si la clave no está configurada, el modelo no
responde, la API falla o devuelve basura, devuelve None — y la etapa 3
cae en la plantilla local. El asistente nunca se queda mudo por un
modelo.

EL MODELO SOLO SE USA CON CONTEXTO: el pipeline únicamente llama acá
cuando el RAG encontró fichas de trámites. Una consulta fuera de tema
—o una que no matchea nada— no gasta la API: se contesta con la
plantilla local. Además, la barra de búsqueda pública (sin sesión) usa
solo plantillas; el modelo queda para usuarios logueados.

Cuando Groq falla (clave vencida, cuota, red), se anota el momento y
por `COOLDOWN_FALLO` segundos no se vuelve a intentar: sin eso, cada
mensaje de la charla pagaría el timeout completo en la cara del
ciudadano.
"""

import re
import time

import requests
from django.conf import settings

from .groq import pedir
from .prompt import SYSTEM, armar_mensajes, armar_user

__all__ = [
    'SYSTEM',
    'activo',
    'armar_mensajes',
    'armar_user',
    'limpiar_enlaces',
    'redactar',
]

# El modelo no debe devolver enlaces: el sistema agrega la fuente interna
# con el título de la ficha como texto. Estos patrones son la red de
# seguridad por si el proveedor igual manda Markdown, HTML o una URL suelta.
_ENLACE_MARKDOWN = re.compile(
    r'\[([^\]]+)\]\((?:https?://|/)[^)]+\)', re.IGNORECASE
)
_ENLACE_HTML = re.compile(r'<a\b[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_URL = re.compile(r'\b(?:https?://|www\.)\S+', re.IGNORECASE)
_NEGRITA = re.compile(r'\*\*(.+?)\*\*|__(.+?)__', re.DOTALL)
_CODIGO = re.compile(r'`([^`]+)`')


def limpiar_enlaces(texto):
    """Quita enlaces del texto del modelo y deja solo el texto visible.

    No toca los enlaces que arma el sistema en la vista: esos se guardan
    aparte, como `FuenteMensaje`. Acá se limpia únicamente la redacción
    del modelo para que no invente URLs ni recomendaciones externas.
    """
    if not texto:
        return texto

    texto = _ENLACE_HTML.sub(r'\1', texto)
    texto = _ENLACE_MARKDOWN.sub(r'\1', texto)
    texto = _URL.sub('', texto)
    texto = _NEGRITA.sub(lambda m: m.group(1) or m.group(2), texto)
    texto = _CODIGO.sub(r'\1', texto)
    # Por si quedó un marcador suelto (el modelo a veces abre sin cerrar).
    texto = texto.replace('**', '').replace('__', '')
    return re.sub(r'[ \t]{2,}', ' ', texto).strip()

# Segundos sin reintentar tras un fallo (ver docstring).
COOLDOWN_FALLO = 60

# Momento (monotónico) del último fallo; 0.0 = nunca falló.
_ultimo_fallo = 0.0


def activo():
    """¿Hay clave configurada y el asistente está encendido?"""
    return bool(settings.CHATBOT_LLM == 'groq' and settings.GROQ_API_KEY)


def redactar(pregunta, fragmentos, historial=()):
    """La respuesta del modelo, o None si no hay modelo disponible.

    `fragmentos` son los Fragmento recuperados por el RAG (etapa 2) y
    `historial` la charla guardada, para seguir el hilo en
    seguimientos cortos («¿y el plazo?»). El pipeline solo llama acá
    con fragmentos: sin contexto no se gasta la API.
    """
    global _ultimo_fallo

    if not activo():
        return None
    if time.monotonic() - _ultimo_fallo < COOLDOWN_FALLO:
        return None

    try:
        texto = pedir(armar_mensajes(pregunta, fragmentos, historial))
    except (requests.RequestException, ValueError):
        # Sin red, timeout, 401 (clave vencida) o 429 (cuota):
        # se anota el fallo y la etapa 3 usa la plantilla local.
        _ultimo_fallo = time.monotonic()
        return None

    texto = limpiar_enlaces(texto)
    if not texto:
        _ultimo_fallo = time.monotonic()
        return None
    return texto
