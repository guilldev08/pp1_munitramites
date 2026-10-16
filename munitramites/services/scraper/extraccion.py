"""Leer la página de destino: ¿es una ficha? ¿qué dice? ¿qué pide?

El filtro clave es `parece_ficha()`: la página tiene que ser la ficha de
UN trámite y no un índice de sección ni una noticia. Sin eso, un link
«Trámites» que llevaba al listado de la sección terminaba siendo un
trámite con la descripción de relleno.
"""

import re
from urllib.parse import urlparse

from .relevancia import sin_acentos, texto_visible
from .vocabulario import PALABRAS_REQUISITO

# Un índice es casi todo links; una ficha es prosa.
MAXIMO_DENSIDAD_LINKS = 0.5
# Por debajo de esto no hay nada que extraer.
MINIMO_TEXTO = 100


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
    """Textos de requisitos de la página, limpios y acotados."""
    lista = lista_de_requisitos(sopa)
    if lista:
        items = [li.get_text(' ', strip=True) for li in lista.find_all('li')]
    else:
        # Respaldo: <li> sueltos con pinta de requerimiento.
        items = [
            li.get_text(' ', strip=True)
            for li in sopa.find_all('li')
            if any(p in sin_acentos(li.get_text(' ', strip=True).lower())
                   for p in PALABRAS_REQUISITO)
        ]

    limpios, vistos = [], set()
    for item in items:
        item = re.sub(r'\s+', ' ', item).strip(' ·•-')
        clave = sin_acentos(item.lower())
        if not (10 <= len(item) <= 290) or clave in vistos:
            continue
        vistos.add(clave)
        limpios.append(item)
        if len(limpios) == 8:
            break
    return limpios


def descripcion(sopa, nombre_organismo):
    """Meta descripción, el primer párrafo decente, o un texto de fábrica."""
    meta = sopa.find('meta', attrs={'name': 'description'})
    if meta and len((meta.get('content') or '').strip()) > 40:
        return re.sub(r'\s+', ' ', meta['content']).strip()[:500]
    for parrafo in sopa.find_all('p'):
        if parrafo.find_parent(['header', 'footer', 'nav']):
            continue
        texto = re.sub(r'\s+', ' ', parrafo.get_text(' ', strip=True))
        if len(texto) > 60:
            return texto[:500]
    return f'Trámite informado por {nombre_organismo}.'


def titulo(texto, url):
    """Rótulo usable para el trámite (máx. 200 caracteres en el modelo)."""
    texto = re.sub(r'\s+', ' ', texto or '').strip(' .|-–—·>“”"')
    if len(texto) < 8:
        segmento = urlparse(url).path.rstrip('/').split('/')[-1]
        texto = re.sub(r'[-_]+', ' ', segmento).strip().title() or texto
    return texto[:195] or 'Trámite'
