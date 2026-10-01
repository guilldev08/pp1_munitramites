"""Etapa 2 — RECUPERAR: qué fragmentos responden la pregunta.

    normalizar / tokenizar   pasa a minúsculas, quita acentos y palabras de
                             relleno, y agrega los sinónimos del dominio
                             (dni → documento, licencia → conducir, …)
    buscar                   puntúa cada fragmento con BM25 y devuelve los
                             `top_k` que superen el umbral

BM25 es el ranking clásico de búsqueda: premia los términos que aparecen
poco en el índice y los que pesan mucho dentro del fragmento. Con esto el
asistente recupera el contexto; quién redacta la respuesta es la etapa 3.
"""

import math
import re
import unicodedata

from django.conf import settings

from .indexar import obtener_indice

__all__ = ['buscar', 'normalizar', 'tokenizar']

# Palabras de relleno del español (se ignoran al puntuar)
VACIAS = {
    'que', 'como', 'cual', 'cuales', 'donde', 'cuando', 'para', 'por',
    'una', 'uno', 'unos', 'unas', 'del', 'con', 'sin', 'sobre', 'desde',
    'hasta', 'entre', 'muy', 'mas', 'este', 'esta', 'estos',
    'estas', 'ese', 'esa', 'eso', 'aquel', 'the', 'and', 'los', 'las',
    'se', 'su', 'sus', 'lo', 'le', 'les', 'al', 'yo',
    'tu', 'usted', 'nos', 'el', 'la', 'es', 'son', 'ser', 'hay', 'hola',
}

# Sinónimos del dominio: se agregan a la consulta con un peso menor.
# Si mañana aparece un trámite nuevo, se agregan acá sus palabras clave.
SINONIMOS = {
    'dni': ('documento', 'identidad', 'carnet', 'dni'),
    'renovacion': ('renovar', 'renovacion', 'tramitar'),
    'renovar': ('renovacion', 'renovar'),
    'licencia': ('conducir', 'chofer', 'automotor', 'licencia'),
    'conducir': ('licencia', 'chofer', 'automotor'),
    'turno': ('cita', 'turno', 'agenda'),
    'partida': ('acta', 'partida'),
    'nacimiento': ('nacimiento', 'partida', 'acta'),
    'matrimonio': ('matrimonio', 'partida', 'acta'),
    'defuncion': ('defuncion', 'partida', 'acta'),
    'penales': ('antecedentes', 'penales', 'certificado'),
    'antecedentes': ('penales', 'antecedentes', 'certificado'),
    'habilitacion': ('comercio', 'inscripcion', 'habilitacion'),
    'comercio': ('habilitacion', 'inscripcion', 'comercio'),
    'contribucion': ('impuesto', 'tasa', 'rentas', 'tributo'),
    'impuesto': ('contribucion', 'tasa', 'rentas', 'tributo'),
    'impuestos': ('contribucion', 'tasa', 'rentas', 'tributo'),
    'vacuna': ('salud', 'vacunacion', 'vacuna'),
    'salud': ('vacuna', 'vacunacion', 'ministerio'),
    'registro': ('civil', 'registro'),
    'nacional': ('nacion', 'nacional'),
    'municipal': ('municipio', 'municipal'),
    'tramite': ('tramite', 'gestion', 'solicitud'),
    'hacer': ('hacer', 'realizar', 'tramitar'),
    'necesito': ('necesito', 'requisito', 'requerir'),
    'requisitos': ('requisito', 'documentacion', 'necesito'),
}

_PESO_SINONIMO = 0.6
_RE_NO_ALFA = re.compile(r'[^a-z0-9ñ\s]')


def normalizar(texto):
    """Minúsculas, sin acentos, sin puntuación."""
    texto = texto.lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return _RE_NO_ALFA.sub(' ', texto)


def tokenizar(texto):
    """Lista de términos con significado (sin palabras de relleno)."""
    return [
        t for t in normalizar(texto).split()
        if len(t) > 2 and t not in VACIAS
    ]


def _consulta_pesada(pregunta):
    """[(termino, peso)] de la consulta, con sinónimos incluidos."""
    terminos = tokenizar(pregunta)
    salida = [(t, 1.0) for t in terminos]
    for t in terminos:
        for s in SINONIMOS.get(t, ()):
            if s not in terminos:
                salida.append((s, _PESO_SINONIMO))
    return salida


def _puntuar_bm25(pesos, docs_tokens, k1=1.5, b=0.75):
    """BM25 ponderado: cada consulta viene como [(termino, peso)]."""
    n_docs = len(docs_tokens)
    if not n_docs:
        return []

    # Frecuencia de cada término en todo el índice (para el IDF)
    df = {}
    for tokens in docs_tokens:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1

    largos = [len(t) for t in docs_tokens]
    largo_prom = (sum(largos) / n_docs) or 1

    puntajes = []
    for tokens, largo in zip(docs_tokens, largos):
        frec = {}
        for t in tokens:
            frec[t] = frec.get(t, 0) + 1

        score = 0.0
        for termino, peso in pesos:
            tf = frec.get(termino)
            if not tf:
                continue
            aparece = df.get(termino, 0)
            idf = math.log(1 + (n_docs - aparece + 0.5) / (aparece + 0.5))
            denom = tf + k1 * (1 - b + b * largo / largo_prom)
            score += peso * idf * (tf * (k1 + 1)) / denom
        puntajes.append(score)
    return puntajes


def buscar(pregunta, top_k=None, umbral=None):
    """Devuelve [(Fragmento, puntaje)] de los mejores fragmentos.

    Fragmentos por debajo del umbral se descartan: si nada pasa el corte,
    el pipeline responde que no dispone de esa información (criterio de
    «manejo de alucinaciones» del documento).
    """
    top_k = top_k or settings.CHATBOT_TOP_K
    umbral = settings.CHATBOT_UMBRAL if umbral is None else umbral

    fragmentos = obtener_indice()
    if not fragmentos:
        return []

    consulta = _consulta_pesada(pregunta)
    if not consulta:
        return []

    docs_tokens = [tokenizar(f.texto) for f in fragmentos]
    puntajes = _puntuar_bm25(consulta, docs_tokens)

    encontrados = [
        (fragmento, puntaje)
        for fragmento, puntaje in zip(fragmentos, puntajes)
        if puntaje >= umbral
    ]
    encontrados.sort(key=lambda par: par[1], reverse=True)
    return encontrados[:top_k]
