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

Prompts comunes a los dos: responder SOLO con el contexto, contestar lo
que preguntaron (sin repetir siempre la misma fórmula), citar el trámite
fuente y decir «no dispongo de esa información» cuando el contexto no
alcanza (criterios del documento: precisión contextual, manejo de
alucinaciones y cita de fuentes). Además, lo que sale del modelo pasa por
dos filtros antes de mostrarlo: `_sin_eco` (corta los marcadores del
prompt si el modelo los pegó) y `_cifras_ajenas` (toda cifra que no
estuviera en el contexto es invención y se descarta). Si la pregunta es
corta («¿y el plazo?»), se le manda al modelo también la pregunta
anterior del usuario para que sepa de qué habla.
"""

import http.client
import json
import re
import time
import urllib.request
import zlib

from django.conf import settings

__all__ = [
    'INSTRUCCION',
    'LLMHttp',
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
#
# Los puntos que más costó conseguir con Qwen de 1,5B (probado en vivo):
#   · que no escriba en PRIMERA PERSONA del ciudadano («solicito…»,
#     «me dirijo a…») imitando modelos de nota que traiga el contexto,
#   · que no se presente en cada respuesta (desperdicia tokens de CPU),
#   · que se apegue al contexto y diga «no dispongo» en vez de inventar,
#   · que CONTESTE LO QUE PREGUNTARON: con «Para tramitar este trámite
#     necesitás…» servía igual para requisitos, plazos y costos, y todas
#     las respuestas salían idénticas. Por eso la regla 1 pide variar la
#     redacción, y por eso NO hay un ejemplo literal de frase en las
#     reglas: el modelo lo copiaba palabra por palabra en cada turno.
INSTRUCCION = (
    'Sos el asistente virtual de trámites de la provincia de Misiones: '
    'contestás VOS, del lado del municipio, a una persona que pregunta '
    'desde el sitio.\n'
    '\n'
    'Reglas:\n'
    '1. Contestá EXACTAMENTE lo que preguntaron: requisitos si preguntan '
    'por requisitos, plazos si preguntan por plazos, costos, dónde, '
    'cuándo o quién lo resuelve si preguntan por eso. No des siempre la '
    'misma respuesta ni arranques siempre con la misma frase: redactá con '
    'propiedad según lo que se preguntó, y cada idea una sola vez.\n'
    '2. Respondé en español rioplatense, breve y con tono de funcionario '
    'amable, y citá el nombre del trámite del cual sacaste la '
    'información, preferentemente dentro de la frase («según el trámite '
    'X…») y no siempre como cierre.\n'
    '3. Usá EXCLUSIVAMENTE lo que está entre «Contexto:» y «Pregunta:»: '
    'es lo único que sabés. Si te preguntan un costo, un plazo, un '
    'horario o un requisito que NO está escrito ahí, contestá que no '
    'figura en la información disponible y sugerí otro término de '
    'búsqueda. NUNCA inventes montos, fechas ni plazos.\n'
    '4. Nunca escribas en primera persona de quien pide el trámite '
    '(«solicito…», «me dirijo a…», «¿podría asistirme?»): si el contexto '
    'trae un modelo de nota o un texto de ejemplo, es material del trámite '
    'y no tu respuesta.\n'
    '5. Arrancá derecho con la respuesta: no repitas la pregunta, no '
    'escribas las palabras «Contexto:» ni «Pregunta:» (son del formato y '
    'no de la respuesta), no te presentes ni vuelvas a saludar.\n'
    '6. Si la pregunta es corta («¿y el plazo?»), los mensajes anteriores '
    'del usuario dicen de qué hablás: contestala como continuación de esa '
    'charla. La información para responder sale SIEMPRE del bloque '
    '«Contexto:», nunca de los mensajes viejos. Elegí el trámite que '
    'responda a la pregunta: si la nombra, ese; si es genérica, el del '
    'PRIMER fragmento del contexto, que es el más parecido a lo que '
    'preguntaron. Los demás fragmentos son contexto de más.'
)


# El formato del prompt vive en UN solo lugar. Los tres proveedores (el
# dialecto OpenAI que usamos con Ollama/Qwen, Anthropic y Gemini) mandan el
# mismo mensaje de usuario, así que si cambia el formato, cambia acá.
def _contexto(fragmentos):
    """Los fragmentos recuperados, en viñetas."""
    return '\n'.join(f'• {f.texto}' for f in fragmentos)


def _usuario(pregunta, fragmentos):
    """El mensaje de usuario: contexto entre marcas y la pregunta al final.

    Las marcas «Contexto:» y «Pregunta:» son las que la INSTRUCCION le pide
    al modelo que respete: cambiar este formato sin cambiar la INSTRUCCION
    (o al revés) rompe el contrato del prompt.
    """
    return f'Contexto:\n{_contexto(fragmentos)}\n\nPregunta: {pregunta}'


# La charla que se le manda al modelo. Son SÓLO las preguntas del usuario
# (nunca las respuestas del propio asistente) y SÓLO cuando la pregunta
# actual es corta: una consulta completa no necesita el hilo, y las
# respuestas previas eran un vector de alucinación — pasó en vivo, Qwen
# de 1,5B contestó los requisitos de antecedentes penales con la partida
# de nacimiento que había redactado en el turno anterior. Lo que el
# modelo necesita del hilo es el REFERENTE de «¿y el plazo?», y ese está
# en la pregunta anterior del ciudadano.
PREGUNTA_CORTA = 4      # palabras: hasta acá se considera seguimiento
HISTORIAL_PREGUNTAS = 1  # cuántas preguntas previas se mandan
HISTORIAL_LARGO = 300    # caracteres por mensaje viejo


def _mensajes(pregunta, fragmentos, historial=()):
    """Los mensajes del chat: system + (pregunta previa) + pregunta actual.

    El orden lo chequea el test del prompt: `system` primero y la pregunta
    con el contexto RAG siempre la ÚLTIMA. El historial llega de la sesión
    del usuario (mismos mensajes que ve el ciudadano) como dicts con `rol`
    y `texto`; los roles del dialecto OpenAI son 'user' y 'assistant'.
    """
    mensajes = [{'role': 'system', 'content': INSTRUCCION}]

    if len(pregunta.split()) <= PREGUNTA_CORTA:
        previas = [
            str(m.get('texto') or '').strip()
            for m in (historial or [])
            if m.get('rol') == 'usuario' and (m.get('texto') or '').strip()
        ][-HISTORIAL_PREGUNTAS:]
        for texto in previas:
            mensajes.append({
                'role': 'user',
                'content': texto[:HISTORIAL_LARGO],
            })

    mensajes.append({'role': 'user', 'content': _usuario(pregunta, fragmentos)})
    return mensajes


def _combinar(mensajes):
    """Junta mensajes consecutivos del mismo rol en uno solo.

    Anthropic exige que los roles alternen (y acá pueden venir dos
    'user' seguidos: la pregunta previa y la actual); a OpenAI, Ollama y
    Gemini no les molesta, así que el mismo formato sirve a los tres.
    """
    salida = []
    for m in mensajes:
        if salida and salida[-1]['role'] == m['role']:
            salida[-1] = {
                'role': m['role'],
                'content': salida[-1]['content'] + '\n' + m['content'],
            }
        else:
            salida.append(dict(m))
    return salida


class ProveedorLLM:
    """Contrato que cumplen todos los proveedores de generación."""

    def esta_configurado(self) -> bool:
        raise NotImplementedError

    def completar(self, pregunta: str, fragmentos, historial=()) -> str | None:
        """Devuelve el texto de la respuesta, o None si no pudo.

        `historial` es la charla previa de la sesión (dicts con `rol` y
        `texto`): los modelos lo usan para encadenar; la plantilla local
        no lo necesita.
        """
        raise NotImplementedError


def _redaccion(opciones, pregunta):
    """Elegir una variante de forma estable, sin random.

    La MISMA pregunta siempre cae en la misma frase (la charla no
    contradice una respuesta anterior) y preguntas distintas caen en
    frases distintas: sin esto, cuando el modelo se caía, TODAS las
    respuestas salían letra por letra iguales.
    """
    return opciones[zlib.crc32(pregunta.encode('utf-8')) % len(opciones)]


class PlantillaLocal(ProveedorLLM):
    """Respuesta armada con las plantillas del sitio (sin modelo externo).

    Cada caso tiene más de una redacción, y todas arrancan con «Encontré»,
    que es la palabra que chequean los tests de resiliencia.
    """

    def esta_configurado(self):
        return True

    def completar(self, pregunta, fragmentos, historial=()):
        tramites = []
        for f in fragmentos:
            if f.tramite_titulo not in tramites:
                tramites.append(f.tramite_titulo)

        n = len(tramites)

        # Seguimiento corto («¿y el plazo?»): repetir la pregunta suelta
        # no le dice nada al ciudadano, se le citan los trámites.
        if historial and n and len(pregunta.split()) <= PREGUNTA_CORTA:
            nombres = ' y '.join(f'«{t}»' for t in tramites)
            if n == 1:
                return (
                    f'Encontré {nombres}, que es el trámite de lo que '
                    f'venís preguntando. Abrí la ficha para ver los '
                    f'requisitos y los enlaces oficiales.'
                )
            return (
                f'Encontré {n} trámites que pueden servirte: {nombres}. '
                f'Abrí la que más te sirva para ver los requisitos.'
            )

        if n == 1:
            aperturas = (
                f'Encontré el trámite «{tramites[0]}» para «{pregunta}».',
                f'Encontré «{tramites[0]}», que es el trámite que va para '
                f'«{pregunta}».',
                f'Encontré el trámite que corresponde a «{pregunta}»: '
                f'«{tramites[0]}».',
            )
            cierres = (
                'Abrí la ficha para ver los requisitos y los enlaces '
                'oficiales.',
                'En la ficha están los requisitos, el organismo '
                'responsable y los enlaces oficiales.',
                'Revisá la ficha: requisitos, dónde presentar y enlaces '
                'oficiales.',
            )
        else:
            aperturas = (
                f'Encontré {n} trámites relacionados con «{pregunta}».',
                f'Encontré {n} trámites que pueden servirte para '
                f'«{pregunta}».',
            )
            cierres = (
                'Abrí la ficha que más te sirva para ver todos los '
                'requisitos.',
                'Comparalas en las fichas: cada una trae sus requisitos y '
                'enlaces oficiales.',
            )
        return (
            f'{_redaccion(aperturas, pregunta)} '
            f'{_redaccion(cierres, pregunta)}'
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

    # -- Proveedores --------------------------------------------------------
    def _openai(self, pregunta, fragmentos, historial=()):
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
                'messages': _mensajes(pregunta, fragmentos, historial),
                # Temperatura moderada: con 0,2 Qwen redactaba SIEMPRE la
                # misma frase de apertura; muy alta, alucinaba datos.
                'temperature': 0.6,
                # Respuesta corta: en CPU la lentitud crece con los tokens.
                'max_tokens': 256,
            },
            encabezados,
        )
        return cuerpo['choices'][0]['message']['content']

    def _anthropic(self, pregunta, fragmentos, historial=()):
        cuerpo = self._post(
            'https://api.anthropic.com/v1/messages',
            {
                'model': self.config.get('modelo') or 'claude-3-5-haiku-latest',
                'max_tokens': 512,
                'system': INSTRUCCION,
                # Anthropic separa el system y exige roles alternados:
                # los dos 'user' seguidos (pregunta previa + actual) se
                # juntan en uno.
                'messages': _combinar(
                    _mensajes(pregunta, fragmentos, historial)[1:]
                ),
            },
            {
                'x-api-key': self.config['api_key'],
                'anthropic-version': '2023-06-01',
            },
        )
        return cuerpo['content'][0]['text']

    def _gemini(self, pregunta, fragmentos, historial=()):
        modelo = self.config.get('modelo') or 'gemini-1.5-flash'
        base = self.config.get('base_url') or (
            'https://generativelanguage.googleapis.com/v1beta'
        )
        # Gemini llama 'user'/'model' a lo que OpenAI llama
        # 'user'/'assistant'; el system va aparte, igual que Anthropic.
        contenidos = [
            {
                'role': 'user' if m['role'] == 'user' else 'model',
                'parts': [{'text': m['content']}],
            }
            for m in _combinar(_mensajes(pregunta, fragmentos, historial)[1:])
        ]
        cuerpo = self._post(
            f'{base}/models/{modelo}:generateContent',
            {
                'system_instruction': {'parts': [{'text': INSTRUCCION}]},
                'contents': contenidos,
            },
            {'x-goog-api-key': self.config['api_key']},
        )
        return cuerpo['candidates'][0]['content']['parts'][0]['text']

    def completar(self, pregunta, fragmentos, historial=()):
        global _en_fallo_hasta

        if time.monotonic() < _en_fallo_hasta:
            # En cooldown: no se insiste con la red, se contesta ya mismo
            # con la plantilla (ver ESPERA_TRAS_UN_FALLO).
            return None

        proveedor = (self.config.get('proveedor') or '').lower()
        try:
            if proveedor == 'anthropic':
                texto = self._anthropic(pregunta, fragmentos, historial)
            elif proveedor == 'gemini':
                texto = self._gemini(pregunta, fragmentos, historial)
            else:
                # 'openai', 'ollama' y 'custom' hablan el mismo dialecto
                # (chat/completions), así que comparten camino.
                texto = self._openai(pregunta, fragmentos, historial)
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


# La respuesta del modelo se chequea ANTES de mostrarla: son dos formas de
# alucinación que Qwen de 1,5B largó en vivo (probado con preguntas de
# costo y de plazo), aunque el prompt lo prohíba.
#
#   1. cifras que no estaban en el contexto («la tasa es de 20 pesos»),
#   2. eco del propio prompt («Contexto: … Pregunta: …»), que encadena
#      de turno en turno si se guarda en la charla sin limpiar.

_CIFRA = re.compile(r'\d+')

# Números de enumeración («1. DNI vigente», «2) partida»): son formato,
# no datos, así que no se comparan contra el contexto.
_NUM_LISTA = re.compile(r'(?:^|[\s(])(\d+)[.)](?=\s)')


def _cifras_ajenas(texto, contexto):
    """Las cifras de la respuesta que NO aparecen en el contexto.

    El criterio de «manejo de alucinaciones» del documento pide decir
    «no dispongo» antes que inventar: una cifra ajena al contexto es una
    invención segura (el contexto es lo único que el modelo pudo ver).
    """
    conocidas = set(_CIFRA.findall(contexto))
    de_lista = {m.start(1) for m in _NUM_LISTA.finditer(texto)}
    return {
        m.group(0) for m in _CIFRA.finditer(texto)
        if m.start() not in de_lista and m.group(0) not in conocidas
    }


def _parecida(a, b):
    """¿El texto `a` es casi la misma pregunta que `b`? (medido por
    palabras compartidas sobre la más corta de las dos)."""
    def palabras(x):
        return {p for p in re.findall(r'\w+', x.lower()) if len(p) > 2}

    pa, pb = palabras(a), palabras(b)
    if not pa or not pb:
        return False
    return len(pa & pb) / min(len(pa), len(pb)) >= 0.75


def _sin_eco(texto, pregunta):
    """Corta el eco del prompt: si el modelo pegó los marcadores en vez de
    contestar, se queda sólo con lo que venga después de la última
    «Pregunta:».

    En el formato del eco la pregunta repetida ocupa su propia línea (o
    es todo lo que quedó), así que se descarta ANTES de mirar si hay
    respuesta: sin ese paso se confundiría «pregunta + respuesta» con un
    eco puro y se tiraría la respuesta buena.
    """
    if 'Contexto:' not in texto:
        return texto
    if 'Pregunta:' not in texto:
        return ''      # pegó el contexto entero y no contestó nada

    resto = texto.rsplit('Pregunta:', 1)[1].strip()
    linea, _, demas = resto.partition('\n')
    if _parecida(linea, pregunta):
        resto = demas.strip()       # la primera línea era la pregunta ecoada

    if len(resto) < 12 or _parecida(resto, pregunta):
        return ''
    return resto


# Preguntas por un MONTO: si el contexto no trae ninguno, no hace falta
# ni preguntarle al modelo — sólo podría inventarlo (pasó en vivo: «el
# costo es de $50.000.000» por un DNI). La respuesta sale acá mismo:
# es inmediata, determinista y no depende de que el prompt obedezca.
_PREGUNTA_MONTO = re.compile(
    r'cu[aá]nto\s+(?:se\s+)?(?:paga|cuesta|sale|vale)'
    r'|\bcu[aá]nto\s+es\b'
    r'|\bprecio\b',
    re.IGNORECASE,
)

# Un monto SÍ indexado en el contexto: signopeso, «pesos» con número o
# una gratuidad declarada.
_HAY_MONTO = re.compile(
    r'\$\s*\d|\b\d[\d.]*\s*pesos?\b|gratuit',
    re.IGNORECASE,
)

_SIN_DATO = (
    'No dispongo de ese dato en la base de conocimiento de Munitramites: '
    'el monto exacto no está en la ficha indexada. En la ficha del '
    'trámite están los requisitos y los enlaces oficiales donde sí '
    'podés consultarlo.'
)


def generar_respuesta(pregunta, fragmentos, historial=()):
    """Redacta la respuesta; si el proveedor falla o alucina, la plantilla.

    Tres filtros, en orden: primero un monto que sepa que no está
    (responde sin modelo), después los dos del modelo (`_sin_eco` y
    `_cifras_ajenas`); si alguno la descarta, se responde con la
    plantilla local, que sólo repite datos del índice.
    """
    contexto = _contexto(fragmentos)

    if _PREGUNTA_MONTO.search(pregunta) and not _HAY_MONTO.search(contexto):
        return _SIN_DATO

    texto = proveedor().completar(pregunta, fragmentos, historial)

    if texto:
        texto = _sin_eco(texto.strip(), pregunta)
        if texto:
            conocido = contexto + ' ' + ' '.join(
                str(m.get('texto') or '') for m in (historial or ())
            )
            if not _cifras_ajenas(texto, conocido):
                return texto

    return PlantillaLocal().completar(pregunta, fragmentos, historial)
