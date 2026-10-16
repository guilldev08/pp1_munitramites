"""Decidir qué link es un trámite (y castigar los menús).

El scraper viejo «tomaba cualquier cosa»: alcanzaba con que un link
tuviera una palabra suelta («Servicios», «Registro», «Personas») para
que se siguiera. Acá vive el criterio:

    puntaje_link()  fuerte = 2 puntos, débil = 1 (en la URL, la mitad).
                    Un link de menú, cabecera o pie vale la mitad.
    es_ruido()      descarta noticias, PDFs, redes y demás.

Umbral: un candidato necesita PUNTAJE_MINIMO para seguirse (una palabra
fuerte, o dos débiles). Ver vocabulario.py para las listas.
"""

import re
import unicodedata

from .vocabulario import (
    PALABRAS_DEBILES, PALABRAS_FUERTES, PALABRAS_RUIDO, REDES,
)

# Un candidato sin este puntaje no se sigue.
PUNTAJE_MINIMO = 2.0

# Firebird corta en seco en 300: una URL más larga ni entra ni serviría
# truncada.
LARGO_URL_MAXIMO = 290


def sin_acentos(texto):
    """«Oberá» → «Obera»: para comparar y para guardar igual que el seed."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )


def es_ruido(texto):
    """¿El texto o la URL son de algo que nunca es un trámite?"""
    bajo = sin_acentos(texto.lower())
    return any(p in bajo for p in PALABRAS_RUIDO + REDES)


def puntaje_link(texto, url, en_menu=False):
    """Cuánto huele a trámite este link (ver el docstring del módulo)."""
    bajo_texto = sin_acentos(texto.lower())
    bajo_url = sin_acentos(url.lower())
    puntos = 0.0
    for palabra in PALABRAS_FUERTES:
        if palabra in bajo_texto:
            puntos += 2
        elif palabra in bajo_url:
            puntos += 1
    for palabra in PALABRAS_DEBILES:
        if palabra in bajo_texto:
            puntos += 1
        elif palabra in bajo_url:
            puntos += 0.5
    if en_menu:
        puntos *= 0.5
    return puntos


def esta_en_menu(etiqueta):
    """¿El link está en el menú, la cabecera o el pie?"""
    return etiqueta.find_parent(['nav', 'header', 'footer']) is not None


def texto_visible(sopa):
    """Todo el texto de la página, sin scripts ni estilos, en una línea."""
    for etiqueta in sopa.find_all(['script', 'style', 'noscript']):
        etiqueta.decompose()
    return re.sub(r'\s+', ' ', sopa.get_text(' ', strip=True)).strip()
