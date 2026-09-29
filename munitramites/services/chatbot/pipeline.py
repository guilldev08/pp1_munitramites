"""Orquestador del asistente: pregunta → fragmentos → respuesta + fuentes.

    responder(pregunta) → {
        'texto':     str legible para el ciudadano,
        'tramites':  [Tramite] fuentes citadas (enlaceables),
        'fragmentos':[Fragmento] contexto recuperado (lo que usó el LLM),
    }

Reglas de la conversación:

    · saludo y «ayuda» se responden sin buscar en el índice,
    · si el índice devuelve fragmentos, se citan los trámites fuente,
    · si NO hay fragmentos por encima del umbral, se dice explícitamente
      que no se dispone de esa información (nunca se inventa),
    · la charla no se guarda en la base: vive en la sesión del usuario.
"""

from ...models import Tramite
from .generacion import generar_respuesta
from .recuperacion import buscar

__all__ = ['responder']

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


def responder(pregunta):
    """Punto de entrada único del asistente."""
    pregunta = (pregunta or '').strip()

    if not pregunta:
        return {
            'texto': ('Escribí una consulta, por ejemplo: «¿cómo renuevo '
                      'el DNI?».'),
            'tramites': [],
            'fragmentos': [],
        }

    bajo = pregunta.lower()
    if any(p in bajo for p in ('hola', 'buenos dias', 'buenas')):
        return {'texto': _SALUDO, 'tramites': [], 'fragmentos': []}
    if bajo in ('ayuda', 'help'):
        return {'texto': _AYUDA, 'tramites': [], 'fragmentos': []}

    encontrados = buscar(pregunta)

    if not encontrados:
        # Criterio «manejo de alucinaciones»: decir que no se sabe.
        return {'texto': _SIN_INFO, 'tramites': [], 'fragmentos': []}

    fragmentos = [f for f, _ in encontrados]
    return {
        'texto': generar_respuesta(pregunta, fragmentos),
        'tramites': _tramites_fuente(fragmentos),
        'fragmentos': fragmentos,
    }
