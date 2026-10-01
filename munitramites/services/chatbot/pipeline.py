"""Orquestador del asistente: pregunta → fragmentos → respuesta + fuentes.

    responder(pregunta, historial) → {
        'texto':     str legible para el ciudadano,
        'tramites':  [Tramite] fuentes citadas (enlazables),
        'fragmentos':[Fragmento] contexto recuperado (lo que usó el LLM),
    }

Reglas de la conversación:

    · saludo y «ayuda» se responden sin buscar en el índice (pero un
      saludo SEGUIDO de una pregunta no se traga la pregunta),
    · «limpiar» vacía la charla y «gracias»/«chau» tienen su respuesta,
    · si el índice devuelve fragmentos, se citan los trámites fuente,
    · si NO hay fragmentos por encima del umbral, se dice explícitamente
      que no se dispone de esa información (nunca se inventa),
    · un seguimiento corto («¿y el plazo?») se busca junto con lo que se
      preguntó antes, y el historial entero se le pasa al modelo,
    · la charla no se guarda en la base: vive en la sesión del usuario.
"""

import re

from ...models import Tramite
from .generacion import generar_respuesta
from .recuperacion import buscar

__all__ = ['es_limpieza', 'responder']

_SALUDO = (
    '¡Hola! Soy el asistente de trámites de Misiones. Preguntame por un '
    'trámite, por ejemplo: «licencia de conducir» o «partida de nacimiento».'
)

_AYUDA = (
    'Puedo buscar trámites por nombre, tema, requisito u organismo. '
    'Probá con «antecedentes penales», «habilitación comercial» o '
    '«vacunación». Escribí «limpiar» para empezar de nuevo.'
)

_SIN_INFO = (
    'No dispongo de esa información en la base de conocimiento de '
    'Munitramites. Probá con otra palabra (por ejemplo «licencia de '
    'conducir» o «partida de nacimiento») o escribí «ayuda» para ver qué '
    'sé responder.'
)

_GRACIAS = (
    '¡De nada! Seguí preguntando: busco por nombre de trámite, requisito, '
    'tema u organismo.'
)

_DESPEDIDA = (
    '¡Hasta luego! Volvé cuando quieras, acá sigo para resolver dudas de '
    'trámites.'
)

_CHARLA_VACIA = (
    'Listo, vaciamos la charla. ¿Qué trámite necesitás?'
)

# Un saludo sólo a LA PALABRA INICIAL del mensaje («hola, ¿cómo renuevo
# el DNI?» → queda «¿cómo renuevo el DNI?»). El truco es no matchear
# «hola» en cualquier lado: antes, cualquier pregunta que trajera «hola»
# se contestaba con el saludo fijo y la consulta se perdía.
_SALUDO_INICIAL = re.compile(
    r'^\s*[¿¡]?\s*(?:'
    r'buen(?:as|os)\s+(?:d[ií]as|tardes|noches)'
    r'|hola|buenas|buenos|hey|holis'
    r'|d[ií]as|tardes|noches'
    r')\b[\s,;.!¡]*',
    re.IGNORECASE,
)


def _normalizar(texto):
    """Minúsculas y sin signos: para comparar con las palabras clave."""
    return (texto or '').lower().strip(' ¿?¡!.,;:')


def _sin_saludo(texto):
    """El mensaje sin las una o dos palabras de saludo iniciales."""
    resto = texto or ''
    for _ in range(2):  # «hola, buenas» son dos saludos seguidos
        sin = _SALUDO_INICIAL.sub('', resto, count=1)
        if sin == resto:
            break
        resto = sin
    return resto.strip()


def es_limpieza(pregunta):
    """¿El mensaje es la orden de vaciar la charla? (lo promete _AYUDA)."""
    return _normalizar(_sin_saludo(pregunta)) == 'limpiar'


def _preguntas_previas(historial):
    """Las últimas dos preguntas del usuario (sin la actual)."""
    return [
        str(m.get('texto') or '').strip()
        for m in (historial or [])
        if m.get('rol') == 'usuario' and (m.get('texto') or '').strip()
    ][-2:]


def _tramites_fuente(fragmentos):
    """Los trámites citados, en el orden en que fueron recuperados."""
    ids = []
    for f in fragmentos:
        if f.tramite_id not in ids:
            ids.append(f.tramite_id)

    por_id = {
        t.pk: t
        for t in Tramite.objects.filter(pk__in=ids, activo=True)
    }
    return [por_id[pk] for pk in ids if pk in por_id]


def responder(pregunta, historial=None):
    """Punto de entrada único del asistente.

    `historial` es la charla previa de la sesión (dicts con `rol` y
    `texto`, la misma que ve el ciudadano en pantalla): se usa para
    entender seguimientos cortos y se le pasa al modelo para que la
    respuesta siga el hilo de la conversación.
    """
    pregunta = (pregunta or '').strip()

    if not pregunta:
        return {
            'texto': ('Escribí una consulta, por ejemplo: «¿cómo renuevo '
                      'el DNI?».'),
            'tramites': [],
            'fragmentos': [],
        }

    # Primero se desarma el saludo: lo que queda después manda.
    solo = _sin_saludo(pregunta)
    clave = _normalizar(solo)

    if not clave:
        return {'texto': _SALUDO, 'tramites': [], 'fragmentos': []}
    if clave in ('ayuda', 'help'):
        return {'texto': _AYUDA, 'tramites': [], 'fragmentos': []}
    if clave == 'limpiar':
        # La vista vacía la charla al ver esto (es lo que promete _AYUDA);
        # acá sólo se contesta.
        return {'texto': _CHARLA_VACIA, 'tramites': [], 'fragmentos': []}
    if clave == 'gracias':
        return {'texto': _GRACIAS, 'tramites': [], 'fragmentos': []}
    if clave in ('chau', 'adios', 'hasta luego', 'hasta pronto', 'nos vemos'):
        return {'texto': _DESPEDIDA, 'tramites': [], 'fragmentos': []}

    previas = ' '.join(_preguntas_previas(historial))
    consulta = pregunta
    if previas and len(pregunta.split()) <= 4:
        # Seguimiento corto («¿y el plazo?»): sin el tema anterior, la
        # búsqueda no sabe de qué trámite habla.
        consulta = f'{previas} {pregunta}'

    encontrados = buscar(consulta)
    if not encontrados and consulta == pregunta and previas:
        encontrados = buscar(f'{pregunta} {previas}')

    if not encontrados:
        # Criterio «manejo de alucinaciones»: decir que no se sabe.
        return {'texto': _SIN_INFO, 'tramites': [], 'fragmentos': []}

    fragmentos = [f for f, _ in encontrados]
    return {
        'texto': generar_respuesta(pregunta, fragmentos, historial),
        'tramites': _tramites_fuente(fragmentos),
        'fragmentos': fragmentos,
    }
