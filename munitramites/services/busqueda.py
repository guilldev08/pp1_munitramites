"""Búsqueda flexible del catálogo de trámites.

El buscador público y el del panel dejan de exigir el texto exacto: acá
se normaliza (minúsculas, sin tildes, sin puntuación), se toleran plurales
y palabras parciales, se suman sinónimos del dominio y se ordena por
relevancia.

    normalizar / tokenizar / raiz   preparan el texto
    buscar_tramites(queryset, q)    filtra y ordena por relevancia

No toca la base: recibe el queryset ya filtrado por tema/municipio/estado
y devuelve una lista de trámites ordenada. El catálogo es chico (cientos
de filas), así que resolverlo en Python es simple y suficiente.
"""

import re
import unicodedata

__all__ = ['buscar_tramites', 'normalizar', 'raiz', 'tokenizar']

# Palabras de relleno: no aportan a la búsqueda.
VACIAS = {
    'que', 'como', 'cual', 'cuales', 'donde', 'cuando', 'para', 'por',
    'una', 'uno', 'unos', 'unas', 'del', 'con', 'sin', 'sobre', 'desde',
    'hasta', 'entre', 'muy', 'mas', 'este', 'esta', 'estos', 'estas',
    'ese', 'esa', 'eso', 'aquel', 'los', 'las', 'se', 'su', 'sus', 'lo',
    'le', 'les', 'al', 'el', 'la', 'es', 'son', 'ser', 'hay', 'hola',
    'necesito', 'quiero', 'hacer', 'tramitar', 'tramite', 'tramites',
}

# Sinónimos del dominio. Las claves están en su forma «raíz» (singular,
# sin tilde). Se suman a la consulta con menos peso que lo que escribió
# la persona.
SINONIMOS = {
    'dni': ('documento', 'identidad'),
    'documento': ('dni', 'documentacion'),
    'documentacion': ('documento', 'dni'),
    'licencia': ('conducir', 'chofer', 'automotor'),
    'conducir': ('licencia', 'chofer', 'automotor'),
    'chofer': ('licencia', 'conducir'),
    'auto': ('automotor', 'vehiculo'),
    'vehiculo': ('automotor', 'auto'),
    'turno': ('cita', 'agenda'),
    'cita': ('turno', 'agenda'),
    'partida': ('acta', 'nacimiento'),
    'nacimiento': ('partida', 'acta'),
    'matrimonio': ('partida', 'acta', 'casamiento'),
    'defuncion': ('partida', 'acta', 'fallecimiento'),
    'antecedente': ('penal', 'certificado'),
    'penal': ('antecedente', 'certificado'),
    'comercio': ('habilitacion', 'inscripcion', 'rubro'),
    'habilitacion': ('comercio', 'inscripcion'),
    'impuesto': ('tributo', 'tasa', 'renta'),
    'tributo': ('impuesto', 'tasa'),
    'tasa': ('impuesto', 'tributo'),
    'renta': ('impuesto', 'tributo'),
    'vacuna': ('salud', 'vacunacion'),
    'salud': ('vacuna', 'sanitario'),
    'municipio': ('municipal', 'comuna'),
    'municipal': ('municipio', 'comuna'),
}

_PESO_SINONIMO = 0.5
_RE_NO_ALFA = re.compile(r'[^a-z0-9ñ\s]')


def normalizar(texto):
    """Minúsculas, sin acentos y sin puntuación."""
    texto = (texto or '').lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return _RE_NO_ALFA.sub(' ', texto)


def raiz(token):
    """Recorta el plural para que «licencias» y «licencia» sean lo mismo.

    Es una regla liviana, no un stemmer completo: alcanza para el español
    de los trámites y no depende de librerías externas.
    """
    if len(token) > 4 and token.endswith('es') and token[-3] in 'lrndz':
        return token[:-2]
    if len(token) > 3 and token.endswith('s'):
        return token[:-1]
    return token


def tokenizar(texto):
    """Términos con significado, ya en forma de raíz."""
    return [
        raiz(t) for t in normalizar(texto).split()
        if len(t) > 1 and t not in VACIAS
    ]


def _consulta(consulta):
    """[(raíz, peso)] de lo escrito, más los sinónimos con menos peso."""
    tokens = tokenizar(consulta)
    pares = []
    vistos = set()
    for token in tokens:
        if token not in vistos:
            vistos.add(token)
            pares.append((token, 1.0))

    for token in tokens:
        for sinonimo in SINONIMOS.get(token, ()):
            clave = tokenizar(sinonimo)
            if clave and clave[0] not in vistos:
                vistos.add(clave[0])
                pares.append((clave[0], _PESO_SINONIMO))
    return pares


def _coincide(clave_doc, clave_q):
    """Cuánto vale que dos raíces se parezcan (0 = no coincide)."""
    if clave_doc == clave_q:
        return 1.0
    # Palabra parcial / prefijo: «renov» encuentra «renovacion».
    if len(clave_q) >= 3 and clave_doc.startswith(clave_q):
        return 0.7
    if len(clave_doc) >= 4 and clave_q.startswith(clave_doc):
        return 0.6
    return 0.0


def _campos(tramite):
    """[(texto, peso, raíces)] de todo lo que se puede buscar."""
    requisitos = ' '.join(r.descripcion for r in tramite.requisitos.all())
    direcciones = ' '.join(
        f'{d.lugar} {d.direccion} {d.municipio.nombre}'
        for d in tramite.direcciones.all()
    )
    organismo = f'{tramite.organismo.nombre} {tramite.organismo.ocupacion}'
    campos = (
        (tramite.titulo, 6.0),
        (requisitos, 2.0),
        (tramite.descripcion, 1.5),
        (organismo, 1.2),
        (direcciones, 1.0),
        (str(tramite.tema), 0.8),
        (tramite.municipio.nombre, 0.6),
        (tramite.get_modalidad_display(), 0.4),
    )
    return [
        (texto, peso, set(tokenizar(texto)))
        for texto, peso in campos
    ]


def _puntuar(campos, consulta):
    """Puntaje de un trámite: cuánto de la consulta aparece y dónde."""
    total = 0.0
    cubiertos = 0
    for clave, peso in consulta:
        mejor = 0.0
        for _, peso_campo, claves in campos:
            for clave_doc in claves:
                valor = _coincide(clave_doc, clave) * peso_campo
                if valor > mejor:
                    mejor = valor
        if mejor:
            total += peso * mejor
            if peso >= 1.0:
                cubiertos += 1

    originales = sum(1 for _, peso in consulta if peso >= 1.0)
    if originales:
        # Premia cubrir la mayor parte de lo que se escribió.
        total += 4.0 * cubiertos / originales
        if cubiertos == originales:
            total += 3.0
    return total


def buscar_tramites(queryset, consulta):
    """Filtra y ordena el queryset por relevancia para `consulta`.

    Si la consulta no tiene términos útiles (solo palabras de relleno o
    vacía), devuelve el queryset tal cual: no se esconde nada.
    """
    pesos = _consulta(consulta)
    if not pesos:
        return queryset

    frase = ' '.join(normalizar(consulta).split())
    puntuados = []
    vistos = set()
    for tramite in queryset:
        # Un trámite puede venir repetido por sus direcciones: se cuenta una vez.
        if tramite.pk in vistos:
            continue
        vistos.add(tramite.pk)
        campos = _campos(tramite)
        puntaje = _puntuar(campos, pesos)
        if puntaje <= 0:
            continue
        # La frase completa en el título manda: «licencia de conducir».
        if frase and frase in normalizar(tramite.titulo):
            puntaje += 6.0
        puntuados.append((puntaje, tramite))

    puntuados.sort(
        key=lambda par: (-par[0], par[1].titulo.lower(), par[1].pk)
    )
    return [tramite for _, tramite in puntuados]
