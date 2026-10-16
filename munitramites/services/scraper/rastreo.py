"""Traer el HTML y descubrir links: candidatos a trámite y puertas.

`candidatos()` mira la home del sitio y devuelve los links que pasan el
umbral de relevancia (ver relevancia.py), del más prometedor al menos.
`puertas()` busca las páginas de entrada al portal de trámites para
hacer una segunda vuelta sobre ellas.
"""

import re
from urllib.parse import urldefrag, urljoin

import requests
from bs4 import BeautifulSoup

from .relevancia import (
    LARGO_URL_MAXIMO, PUNTAJE_MINIMO, esta_en_menu, es_ruido, puntaje_link,
    sin_acentos,
)
from .vocabulario import PALABRAS_PUERTA

# Navegador común: varios sitios oficiales rechazan al agente por defecto
# de requests (el 403 de argentina.gob.ar era eso).
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')


def traer(url):
    """HTML de una URL, o None si el sitio no contesta.

    Nunca corta el pase: un sitio caído es una fila en el resumen, no un
    traceback.
    """
    try:
        respuesta = requests.get(
            url, headers={'User-Agent': UA}, timeout=15,
        )
        respuesta.raise_for_status()
    except requests.RequestException:
        return None
    if 'html' not in respuesta.headers.get('Content-Type', 'html'):
        return None
    return respuesta.text


def candidatos(html, base):
    """Links del sitio con pinta de trámite, del más prometedor al menos."""
    sopa = BeautifulSoup(html, 'html.parser')
    vistos, salida = set(), []
    for a in sopa.find_all('a', href=True):
        texto = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or len(texto) < 5 or url in vistos:
            continue
        if len(url) > LARGO_URL_MAXIMO or es_ruido(url):
            continue
        puntos = puntaje_link(texto, url, en_menu=esta_en_menu(a))
        if puntos < PUNTAJE_MINIMO:
            continue
        vistos.add(url)
        salida.append({'texto': texto, 'url': url, 'puntaje': puntos})
    salida.sort(key=lambda c: -c['puntaje'])
    return salida


def puertas(html, base, limite=3):
    """Links de entrada al portal de trámites del sitio (segunda vuelta)."""
    sopa = BeautifulSoup(html, 'html.parser')
    salida, vistos = [], set()
    for a in sopa.find_all('a', href=True):
        texto = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or url in vistos or url == base:
            continue
        if len(url) > LARGO_URL_MAXIMO or es_ruido(f'{texto} {url}'):
            continue
        bajo = sin_acentos(f'{texto} {url}'.lower())
        if any(p in bajo for p in PALABRAS_PUERTA):
            vistos.add(url)
            salida.append(url)
            if len(salida) == limite:
                break
    return salida
