"""Etapa 3 — GENERAR: redactar la respuesta usando solo el contexto.

Hay dos proveedores detrás de la MISMA interfaz:

    PlantillaLocal   respaldo: sin dependencias, sin costo, sin internet.
                     Redacta a partir de los fragmentos recuperados y se usa
                     cuando no hay proveedor o si el modelo falla.
    LLMHttp          conexión real con un modelo de lenguaje. Se activa
                     sola cuando `settings.CHATBOT_LLM` trae proveedor.
                     Habla con OpenAI, Anthropic, Gemini o cualquier
                     endpoint compatible: Ollama (el que usamos, con Qwen
                     corriendo local), vLLM, proxy propio.

Prompts comunes a los dos: responder SOLO con el contexto, citar el trámite
fuente y decir «no dispongo de esa información» cuando el contexto no
alcanza (criterios del documento: precisión contextual, manejo de
alucinaciones y cita de fuentes).
"""

import http.client
import json
import time
import urllib.error
import urllib.request

from django.conf import settings

__all__ = [
    'PlantillaLocal',
    'ProveedorLLM',
    'generar_respuesta',
    'proveedor',
]

# Tras un fallo no se vuelve a tocar la red durante estos segundos. Sin
# esto, mientras el modelo no esté disponible cada consulta paga el tiempo
# muerto del resolver (p. ej. ~4 s buscando el host `ollama` que no
# existe) para terminar cayendo igual en la plantilla. Con el cooldown,
# el primer intento cuesta lo que cueste y los siguientes responden ya.
# Si el modelo vuelve, al vencer el plazo se reintenta solo.
ESPERA_TRAS_UN_FALLO = 60  # segundos

# time.monotonic() hasta el que no se insiste con el proveedor.
_en_fallo_hasta = 0.0

# Instrucción que se manda junto al contexto (es la misma para todos los
# proveedores, así la respuesta cambie de modelo o no).
INSTRUCCION = (
    'Sos el asistente virtual de trámites de la provincia de Misiones. '
    'Respondé en español rioplatense, breve y con tono de funcionario '
    'amable. Usá EXCLUSIVAMENTE la información del contexto que te paso; '
    'si el contexto no alcanza para responder, decí que no disponés de esa '
    'información y sugerí otro término de búsqueda. Citá siempre el nombre '
    'del trámite del cual sacaste la información.'
)


class ProveedorLLM:
    """Contrato que cumplen todos los proveedores de generación."""

    def esta_configurado(self) -> bool:
        raise NotImplementedError

    def completar(self, pregunta: str, fragmentos) -> str | None:
        """Devuelve el texto de la respuesta, o None si no pudo."""
        raise NotImplementedError


class PlantillaLocal(ProveedorLLM):
    """Respuesta armada con las plantillas del sitio (sin modelo externo)."""

    def esta_configurado(self):
        return True

    def completar(self, pregunta, fragmentos):
        tramites = []
        for f in fragmentos:
            if f.tramite_titulo not in tramites:
                tramites.append(f.tramite_titulo)

        n = len(tramites)
        plural = 's' if n != 1 else ''
        if n == 1:
            return (
                f'Encontré el trámite «{tramites[0]}» para «{pregunta}». '
                'Abrí la ficha para ver los requisitos y los enlaces '
                'oficiales.'
            )
        return (
            f'Encontré {n} trámites relacionados con «{pregunta}». '
            f'Abrí la ficha que más te sirva para ver todos los requisitos.'
        )


class LLMHttp(ProveedorLLM):
    """Conexión con un modelo de lenguaje por HTTP (sin SDK).

    La configuración sale de `settings.CHATBOT_LLM`:

        {
            'proveedor': 'ollama' | 'openai' | 'anthropic' | 'gemini' | 'custom',
            'api_key':   '',          # Ollama no pide clave
            'modelo':    'qwen2.5:1.5b',
            'base_url':  'http://ollama:11434/v1',
            'timeout':   60,
        }

    `ollama` y `custom` hablan el dialecto OpenAI (chat/completions) y no
    exigen api_key: alcanza con la URL. Cualquier fallo (red, clave
    vencida, JSON raro) devuelve None: el pipeline cae en la plantilla
    local y la conversación sigue andando.
    """

    def __init__(self, config):
        self.config = config

    def esta_configurado(self):
        proveedor = (self.config.get('proveedor') or '').lower()
        if not proveedor:
            return False
        if proveedor in ('ollama', 'custom'):
            # Local o endpoint propio: no hay clave que validar, solo hace
            # falta saber a qué URL pegarle.
            return bool(self.config.get('base_url'))
        return bool(self.config.get('api_key'))

    # -- HTTP ---------------------------------------------------------------
    def _post(self, url, payload, headers):
        datos = json.dumps(payload).encode('utf-8')
        peticion = urllib.request.Request(
            url, data=datos, method='POST',
            headers={'Content-Type': 'application/json', **headers},
        )
        with urllib.request.urlopen(
            peticion, timeout=self.config.get('timeout', 20)
        ) as respuesta:
            return json.loads(respuesta.read().decode('utf-8'))

    def _mensajes(self, pregunta, fragmentos):
        contexto = '\n'.join(f'• {f.texto}' for f in fragmentos)
        return [
            {'role': 'system', 'content': INSTRUCCION},
            {
                'role': 'user',
                'content': f'Contexto:\n{contexto}\n\nPregunta: {pregunta}',
            },
        ]

    # -- Proveedores --------------------------------------------------------
    def _openai(self, pregunta, fragmentos, compatible=False):
        """Dialecto OpenAI: lo hablan OpenAI, Ollama, vLLM y los proxies."""
        base = self.config.get('base_url') or 'https://api.openai.com/v1'
        encabezados = {}
        clave = self.config.get('api_key')
        if clave:
            encabezados['Authorization'] = f'Bearer {clave}'
        cuerpo = self._post(
            f'{base}/chat/completions',
            {
                'model': self.config.get('modelo') or 'gpt-4o-mini',
                'messages': self._mensajes(pregunta, fragmentos),
                'temperature': 0.2,
                # Respuesta corta: en CPU la lentitud crece con los tokens.
                'max_tokens': 256,
            },
            encabezados,
        )
        return cuerpo['choices'][0]['message']['content']

    def _anthropic(self, pregunta, fragmentos):
        contexto = '\n'.join(f'• {f.texto}' for f in fragmentos)
        cuerpo = self._post(
            'https://api.anthropic.com/v1/messages',
            {
                'model': self.config.get('modelo') or 'claude-3-5-haiku-latest',
                'max_tokens': 512,
                'system': INSTRUCCION,
                'messages': [{
                    'role': 'user',
                    'content': f'Contexto:\n{contexto}\n\nPregunta: {pregunta}',
                }],
            },
            {
                'x-api-key': self.config['api_key'],
                'anthropic-version': '2023-06-01',
            },
        )
        return cuerpo['content'][0]['text']

    def _gemini(self, pregunta, fragmentos):
        contexto = '\n'.join(f'• {f.texto}' for f in fragmentos)
        modelo = self.config.get('modelo') or 'gemini-1.5-flash'
        base = self.config.get('base_url') or (
            'https://generativelanguage.googleapis.com/v1beta'
        )
        cuerpo = self._post(
            f'{base}/models/{modelo}:generateContent',
            {
                'system_instruction': {'parts': [{'text': INSTRUCCION}]},
                'contents': [{
                    'parts': [{
                        'text': f'Contexto:\n{contexto}\n\nPregunta: {pregunta}',
                    }],
                }],
            },
            {'x-goog-api-key': self.config['api_key']},
        )
        return cuerpo['candidates'][0]['content']['parts'][0]['text']

    def completar(self, pregunta, fragmentos):
        global _en_fallo_hasta

        if time.monotonic() < _en_fallo_hasta:
            # En cooldown: no se insiste con la red, se contesta ya mismo
            # con la plantilla (ver ESPERA_TRAS_UN_FALLO).
            return None

        proveedor = (self.config.get('proveedor') or '').lower()
        try:
            if proveedor == 'anthropic':
                texto = self._anthropic(pregunta, fragmentos)
            elif proveedor == 'gemini':
                texto = self._gemini(pregunta, fragmentos)
            else:
                # 'openai', 'ollama' y 'custom' hablan el mismo dialecto
                # (chat/completions), así que comparten camino.
                texto = self._openai(pregunta, fragmentos)
        except (OSError, ValueError, KeyError, IndexError, TypeError,
                http.client.HTTPException):
            # Cubre todo lo que puede fallar de punta a punta: sin
            # conexión (OSError/URLError), modelo que se pasa del timeout
            # (TimeoutError), respuesta cortada a mitad (HTTPException) o
            # JSON raro (ValueError/KeyError). Responde la plantilla y
            # queda el cooldown andando para no repetir la espera.
            _en_fallo_hasta = time.monotonic() + ESPERA_TRAS_UN_FALLO
            return None

        _en_fallo_hasta = 0.0   # anduvo: la próxima también se intenta
        return texto


def proveedor() -> ProveedorLLM:
    """El proveedor activo: LLM si está configurado, plantilla si no."""
    config = getattr(settings, 'CHATBOT_LLM', {}) or {}
    llm = LLMHttp(config)
    return llm if llm.esta_configurado() else PlantillaLocal()


def generar_respuesta(pregunta, fragmentos):
    """Redacta la respuesta; si el proveedor falla, usa la plantilla."""
    texto = proveedor().completar(pregunta, fragmentos)
    if texto:
        return texto.strip()
    return PlantillaLocal().completar(pregunta, fragmentos)
