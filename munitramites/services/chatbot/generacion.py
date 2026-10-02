"""Etapa 3 — GENERAR: redactar la respuesta usando solo el contexto.

`PlantillaLocal` arma el texto con las plantillas del sitio a partir de
los fragmentos recuperados: sin dependencias, sin costo, sin internet y
sin modelo propio. Si algún día el asistente se conecta a un servicio
de lenguaje aparte, el punto de conexión es `generar_respuesta`: ni la
vista ni el RAG cambian.

La redacción cumple los criterios del documento: contestar lo que
preguntaron (con más de una variante, para no repetir siempre la misma
fórmula), citar el trámite fuente y decir «no dispongo de esa
información» cuando el contexto no alcanza (precisión contextual,
manejo de alucinaciones y cita de fuentes).

Además hay un corte ANTES de redactar: una pregunta por MONTO que el
contexto no trae se contesta con «no dispongo» de entrada — una cifra
que no está indexada es, por definición, una invención (pasó en vivo:
«$50.000.000» por renovar el DNI).
"""

import re
import zlib

__all__ = [
    'PlantillaLocal',
    'generar_respuesta',
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


# Preguntas por un MONTO: si el contexto no trae ninguno, no hace falta
# redactar una respuesta — sólo podría inventarla (pasó en vivo: «el
# costo es de $50.000.000» por un DNI). La respuesta sale acá mismo:
# es inmediata, determinista y no depende de que ninguna frase obedezca.
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

    Primero el corte de montos (si la pregunta pide un precio y el
    contexto no lo trae, «no dispongo» sin redactar); después la
    plantilla local, que sólo repite datos del índice.
    """
    if _PREGUNTA_MONTO.search(pregunta) and not _HAY_MONTO.search(
        _contexto(fragmentos)
    ):
        return _sin_dato(pregunta)

    return PlantillaLocal().completar(pregunta, fragmentos, historial)
