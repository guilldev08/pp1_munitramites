"""Etapa 3 — GENERAR: redactar la respuesta usando solo el contexto.

`PlantillaLocal` arma el texto con las plantillas del sitio a partir de
los fragmentos recuperados: sin dependencias, sin costo, sin internet y
sin modelo propio. Si `CHATBOT_LLM='groq'`, el texto lo redacta
el modelo de Groq (vía `llm.redactar`) con las MISMAS reglas metidas en
el prompt
del modelo: que los datos de trámites salgan solo del contexto, que cite
los trámites y que diga «no dispongo» cuando no alcanza. Si el modelo
no está disponible o se cae, se vuelve a la plantilla local sin que el
ciudadano se entere.

La redacción cumple los criterios del documento: contestar lo que
preguntaron (con más de una variante, para no repetir siempre la misma
fórmula), citar el trámite fuente y decir «no dispongo de esa
información» cuando el contexto no alcanza (precisión contextual,
manejo de alucinaciones y cita de fuentes).

Hay DOS puertas de entrada:

    generar_respuesta(pregunta, fragmentos, historial)  con contexto
    generar_sin_contexto(pregunta, historial)           sin contexto

En la primera, con el modelo activo el pedido sale PRIMERO hacia Groq
—el modelo redacta con libertad citando lo que haya— y el corte
determinista de montos recién corre si no hay modelo: una pregunta por
un monto que el contexto no trae no puede redactarse la plantilla
(pasó en vivo: «$50.000.000» por renovar el DNI) y el prompt del
modelo prohíbe inventar cifras, así que con modelo alcanza con eso.

La segunda es la charla libre: una consulta que no trajo ninguna ficha
igual puede contestarse con el modelo («¿qué es este portal?»,
preguntas generales, seguimientos sin datos) — nunca inventando fichas.
Sin modelo devuelve None y el pipeline responde con su «no encontré»
de siempre.
"""

import re
import zlib

from . import llm

__all__ = [
    'PlantillaLocal',
    'generar_respuesta',
    'generar_sin_contexto',
]

# Consultas de seguimiento corto («¿y el plazo?»): hasta acá la
# plantilla trata la pregunta como continuación de la charla, y en vez
# de repetirla suelta cita los trámites que encontró.
PREGUNTA_CORTA = 4      # palabras


def _contexto(fragmentos):
    """Los fragmentos recuperados, en viñetas."""
    return '\n'.join(f'• {f.texto}' for f in fragmentos)


def _redaccion(opciones, pregunta):
    """Elegir una variante de forma estable, sin random.

    La MISMA pregunta siempre cae en la misma frase (la charla no
    contradice una respuesta anterior) y preguntas distintas caen en
    frases distintas: sin esto, TODAS las respuestas salían letra por
    letra iguales y el asistente parecía un bot roto.
    """
    return opciones[zlib.crc32(pregunta.encode('utf-8')) % len(opciones)]


def _citar(texto, limite=60):
    """La consulta recortada, para citarla dentro de una respuesta."""
    texto = (texto or '').strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + '…'


class PlantillaLocal:
    """Respuesta armada con las plantillas del sitio (sin modelo externo).

    Cada caso tiene más de una redacción, y todas arrancan con «Encontré»,
    que es la palabra que chequean los tests de resiliencia.
    """

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


# Preguntas por un MONTO: si el contexto no trae ninguno, la plantilla
# local no puede redactar nada — sólo podría inventarla (pasó en vivo:
# «el costo es de $50.000.000» por un DNI). Con modelo activo este
# corte no hace falta: el prompt prohíbe inventar cifras y el modelo
# contesta con «no dispongo» él mismo. Sin modelo, la respuesta sale
# acá mismo: inmediata, determinista y sin depender de que ninguna
# frase obedezca.
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
    'No dispongo del monto de «{consulta}»: la base no indexa montos. '
    'En la ficha del trámite están los requisitos y los enlaces '
    'oficiales donde sí podés consultarlo.',
    'No dispongo de ese dato por «{consulta}»: los montos no están en '
    'las fichas indexadas. Mirá la ficha del trámite y sus enlaces '
    'oficiales, ahí sí figura.',
    'No dispongo de ese monto para «{consulta}»: las fichas indexadas '
    'no traen precios. Fijate en la ficha del trámite y en sus enlaces '
    'oficiales, que ahí sí está publicado.',
)


def _sin_dato(pregunta):
    """Idea de `pipeline._sin_informacion`: con la consulta a la vista.

    Dos preguntas de precio distintas no pueden recibir la misma frase
    clonada (se veía un bot roto): la respuesta cita lo que se preguntó
    y elige la variante de forma estable por la consulta.
    """
    cita = _citar(pregunta)
    return _redaccion(_SIN_DATO, cita).format(consulta=cita)


def generar_respuesta(pregunta, fragmentos, historial=()):
    """Redacta la respuesta; nunca por encima de lo que está indexado.

    Orden: primero el modelo —Groq, si está configurado—
    que redacta con libertad usando el contexto. Sin modelo (o si se
    cayó), el corte determinista de montos —si la pregunta pide un
    precio y el contexto no lo trae, «no dispongo» sin redactar— y
    después la plantilla local, que sólo repite datos del índice.
    """
    texto = llm.redactar(pregunta, fragmentos, historial)
    if texto:
        return texto

    if _PREGUNTA_MONTO.search(pregunta) and not _HAY_MONTO.search(
        _contexto(fragmentos)
    ):
        return _sin_dato(pregunta)

    return PlantillaLocal().completar(pregunta, fragmentos, historial)


def generar_sin_contexto(pregunta, historial=()):
    """Sin fragmentos: con modelo, charla libre; sin modelo, None.

    Es la puerta de respuesta abierta del asistente: una consulta que
    el índice no pudo responder («¿qué es Munitramites?», una duda
    general, un saludo con pregunta) no se contesta con la frase
    pregrabada de «no encontré nada» si hay modelo — el prompt le
    prohíbe inventar fichas, así que puede explicar, orientar y
    conversar sin pasarse de la raya. Sin modelo (o si el modelo se
    cae), el pipeline cae en su respuesta determinista de siempre.
    """
    return llm.redactar(pregunta, (), historial)
