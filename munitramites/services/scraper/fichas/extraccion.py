"""Leer la página de destino: ¿es una ficha? ¿qué dice? ¿qué pide?

Todo se lee del CONTENIDO de la ficha, no del texto del link: en los
portales el link envuelve el menú entero, así que el título sale del
`<title>`/`<h1>` de la página y no de lo que decía el link. Los
requisitos salen de la lista que sigue a «Requisitos», y la descripción
del primer párrafo con sustancia (nunca de la bajada del sitio).
"""

import re
from urllib.parse import urljoin, urlparse

from ..busqueda.relevancia import normalizar, sin_acentos, texto_visible
from ..busqueda.vocabulario import (
    PALABRAS_CASCARA, PALABRAS_RELLENO, PALABRAS_REQUISITO, PALABRAS_SECCION,
    PALABRAS_TURNO, TITULOS_GENERICOS,
)

# Un índice es casi todo links; una ficha es prosa.
MAXIMO_DENSIDAD_LINKS = 0.5
# Por debajo de esto no hay nada que extraer.
MINIMO_TEXTO = 100
# Un párrafo más corto que esto es un rótulo, no una descripción.
MINIMO_DESCRIPCION = 50
MAXIMO_DESCRIPCION = 500
MAXIMO_TITULO = 195
MAXIMO_REQUISITOS = 8
# Más palabras que esto en un rótulo es un volcado de menú.
MAXIMAS_PALABRAS_TITULO = 12


def parece_ficha(sopa):
    """¿La página es la ficha de UN trámite, o un índice/una sección?

    Es ficha si trae la lista de requisitos, o si tiene prosa suficiente
    que habla del trámite. Un índice de sección es casi todo links y se
    descarta.
    """
    if lista_de_requisitos(sopa):
        return True
    texto = texto_visible(sopa)
    if len(texto) < MINIMO_TEXTO:
        return False
    if _densidad_de_links(sopa, texto) > MAXIMO_DENSIDAD_LINKS:
        return False
    bajo = sin_acentos(texto.lower())
    return 'requisit' in bajo or 'tramite' in bajo


def _densidad_de_links(sopa, texto):
    """Qué proporción del texto son links (sin contar menú, cabecera ni pie)."""
    if not texto:
        return 1.0
    largo_links = 0
    for enlace in sopa.find_all('a'):
        if enlace.find_parent(['nav', 'header', 'footer']):
            continue
        largo_links += len(enlace.get_text(' ', strip=True))
    return largo_links / len(texto)


def lista_de_requisitos(sopa):
    """La lista <ul>/<ol> que sigue al encabezado «Requisitos» (o similar)."""
    for encabezado in sopa.find_all(['h2', 'h3', 'h4']):
        rotulo = sin_acentos(encabezado.get_text(' ', strip=True).lower())
        if 'requisit' not in rotulo and 'que necesit' not in rotulo:
            continue
        hermano = encabezado.find_next_sibling()
        while hermano is not None:
            if hermano.name in ('h2', 'h3', 'h4'):
                break
            if hermano.name in ('ul', 'ol'):
                return hermano
            if hermano.name in ('div', 'section'):
                dentro = hermano.find(['ul', 'ol'])
                if dentro:
                    return dentro
            hermano = hermano.find_next_sibling()
    return None


def requisitos(sopa):
    """Textos de requisitos de la página, limpios y sin repetir.

    Primero la lista que sigue a «Requisitos». Si no hay, un respaldo
    estricto: una lista corta donde TODOS los ítems son requerimientos.
    (El respaldo viejo tomaba cualquier <li> con «foto» o «turno» y
    colaba «Galería de fotos» o «Turno online» entre los requisitos.)
    """
    lista = lista_de_requisitos(sopa)
    if lista is not None:
        items = [li.get_text(' ', strip=True) for li in lista.find_all('li')]
        return _limpiar_requisitos(items, exigir_pista=False)
    return _limpiar_requisitos(_items_de_requisitos(sopa), exigir_pista=True)


def _items_de_requisitos(sopa):
    """Respaldo: listas donde TODOS los ítems parecen un requerimiento.

    Un menú de links también puede parecerlo («Guías de trámites», «DNI,
    Nuevo Ejemplar, Denuncia…»): si la mitad o más de los ítems son links,
    es un menú y no una lista de requisitos.
    """
    for lista in sopa.find_all(['ul', 'ol']):
        if lista.find_parent(['nav', 'header', 'footer', 'aside']):
            continue
        items = lista.find_all('li')
        if len(items) < 2:
            continue
        if sum(1 for li in items if li.find('a', href=True)) * 2 >= len(items):
            continue
        textos = [li.get_text(' ', strip=True) for li in items]
        if all(_parece_requisito(texto) for texto in textos):
            return textos
    return []


def _parece_requisito(texto):
    """Un requerimiento: ni cáscara de menú, ni un rótulo suelto."""
    bajo = sin_acentos(texto.lower())
    return (
        10 <= len(texto) <= 290
        and not any(p in bajo for p in PALABRAS_CASCARA)
        and any(p in bajo for p in PALABRAS_REQUISITO)
    )


def _limpiar_requisitos(items, exigir_pista):
    """Normaliza, filtra cáscara y saca repetidos (sin acentos ni mayúsculas)."""
    limpios, vistos = [], set()
    for item in items:
        item = re.sub(r'\s+', ' ', item).strip(' ·•-–—')
        if exigir_pista and not _parece_requisito(item):
            continue
        bajo = sin_acentos(item.lower())
        if not (10 <= len(item) <= 290) or bajo in vistos:
            continue
        if any(p in bajo for p in PALABRAS_CASCARA):
            continue
        vistos.add(bajo)
        limpios.append(item)
        if len(limpios) == MAXIMO_REQUISITOS:
            break
    return limpios


def descripcion(sopa):
    """Primer párrafo con sustancia del contenido, o la meta, o nada.

    El párrafo tiene que ser del contenido (nunca del menú, la cabecera,
    el pie o una barra lateral) y no puede ser la bajada del sitio.
    Devuelve '' si la página no trae una descripción propia: el llamador
    decide qué hacer, acá no se inventa relleno.
    """
    for parrafo in sopa.find_all('p'):
        if parrafo.find_parent(['header', 'footer', 'nav', 'aside']):
            continue
        # Un párrafo con dos links es una lista de descargas, no prosa.
        if len(parrafo.find_all('a')) >= 2:
            continue
        texto = re.sub(r'\s+', ' ', parrafo.get_text(' ', strip=True))
        if _es_descripcion(texto):
            return texto[:MAXIMO_DESCRIPCION]
    meta = sopa.find('meta', attrs={'name': 'description'})
    if meta:
        texto = re.sub(r'\s+', ' ', (meta.get('content') or '')).strip()
        if _es_descripcion(texto):
            return texto[:MAXIMO_DESCRIPCION]
    return ''


def _es_descripcion(texto):
    """¿El texto sirve como descripción, o es relleno del sitio?"""
    if len(texto) < MINIMO_DESCRIPCION:
        return False
    bajo = sin_acentos(texto.lower())
    if any(p in bajo for p in PALABRAS_RELLENO):
        return False
    # «Polonia 1223 - Posadas - contaduria@misiones.gov.ar»: el pie de
    # contacto del organismo no describe ningún trámite.
    if '@' in texto:
        return False
    # «… - Argentina - Año 2026»: el pie de todas las páginas del sitio.
    if re.search(r'\bano 20\d\d\b', bajo):
        return False
    return True


def titulo(sopa, texto_link, url, evitar=''):
    """Nombre del trámite: manda el <title> de la página.

    El <title> es el nombre de la página; el <h1> y el texto del link son
    el respaldo (el link es el menos confiable: arrastra el menú). De los
    respaldos gana el más específico, porque a veces el <h1> es escueto
    («Antecedentes») y el link dice más («Certificado de antecedentes
    penales»). `evitar` descarta el nombre del organismo, que los sitios
    repiten en el <title> de todas sus páginas.
    """
    evitar = normalizar(evitar)
    documento = _limpiar_rotulo(_titulo_documento(sopa))
    respaldos = [
        limpio for limpio in map(
            _limpiar_rotulo, (_encabezado(sopa), texto_link),
        )
        if _titulo_util(limpio) and normalizar(limpio) != evitar
    ]
    if _titulo_util(documento) and normalizar(documento) != evitar:
        # El <title> manda, salvo que sea un acrónimo («INSSJP») y el
        # <h1>/el link digan el nombre completo del trámite.
        mas_largo = max(respaldos, key=len) if respaldos else ''
        if len(mas_largo) < 2 * len(documento):
            return documento[:MAXIMO_TITULO]
        return mas_largo[:MAXIMO_TITULO]
    if respaldos:
        return max(respaldos, key=len)[:MAXIMO_TITULO]
    return _titulo_desde_url(url)[:MAXIMO_TITULO]


def _titulo_documento(sopa):
    """El <title> sin el sufijo del sitio («Trámite - Organismo» → «Trámite»)."""
    if not sopa.title:
        return ''
    partes = re.split(
        r'\s+[|·–—]\s+|\s+-\s+', sopa.title.get_text(' ', strip=True),
    )
    return partes[0] if partes else ''


def _encabezado(sopa):
    for nivel in ('h1', 'h2'):
        nodo = sopa.find(nivel)
        if nodo:
            return nodo.get_text(' ', strip=True)
    return ''


def _limpiar_rotulo(texto):
    """Saca «Ver más», flechas y espacios de sobra de un rótulo."""
    texto = re.sub(r'\s+', ' ', texto or '').strip()
    texto = re.sub(r'(?i)\b(ver|leer|saber)\s+m[aá]s\b.*$', '', texto)
    return texto.strip(' .|-–—·>»“”"→←')


def _titulo_util(titulo):
    """¿Sirve como nombre de un trámite?"""
    if len(titulo) < 5 or len(titulo) > 90:
        return False
    if re.match(r'https?://', titulo, re.I):
        return False
    if len(titulo.split()) > MAXIMAS_PALABRAS_TITULO:
        return False
    bajo = sin_acentos(titulo.lower())
    if bajo in TITULOS_GENERICOS:
        return False
    if any(p in bajo for p in PALABRAS_CASCARA):
        return False
    # Un titular de noticia en mayúsculas («SAMSA INSTALA NUEVO…»).
    if titulo.isupper() and len(titulo.split()) > 4:
        return False
    # Dos o más palabras de sección: es un menú, no un trámite.
    return sum(1 for p in PALABRAS_SECCION if p in bajo) < 2


def _titulo_desde_url(url):
    segmento = urlparse(url).path.rstrip('/').split('/')[-1]
    return re.sub(r'[-_]+', ' ', segmento).strip().title() or 'Trámite'


def enlaces(sopa, url):
    """(enlace de turnos, enlace oficial) que ofrece la ficha.

    El turno puede estar en la propia URL («/turnos/licencia») o ser un
    botón de la página («Turno online» → el sistema de turnos).
    """
    turnos = url if 'turno' in url.lower() else ''
    for enlace in sopa.find_all('a', href=True):
        href = urljoin(url, (enlace.get('href') or '').strip())
        if not href.startswith('http') or href == url:
            continue
        texto = ' '.join(enlace.get_text(' ', strip=True).split())
        bajo = sin_acentos(f'{texto} {href}'.lower())
        if any(p in bajo for p in PALABRAS_TURNO):
            turnos = turnos or href
    return turnos, url
