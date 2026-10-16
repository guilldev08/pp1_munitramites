"""Deducir tema, municipio y modalidad del trámite.

Los trámites del scraping no vienen con estos campos: se completan con
lo que se sabe del organismo y del link. Se pueden corregir después
desde el Centro de Trámites del panel.
"""

from munitramites.models import Municipio, Tema

from .relevancia import sin_acentos
from .vocabulario import TEMAS_POR_PALABRA


def tema_para(texto):
    """Tema del catálogo que mejor calce con el organismo y el link."""
    bajo = sin_acentos(texto.lower())
    for nombre, palabras in TEMAS_POR_PALABRA:
        if any(p in bajo for p in palabras):
            return Tema.objects.get_or_create(nombre=nombre)[0]
    return Tema.objects.get_or_create(nombre='Documentación')[0]


def municipio_para(nombre_organismo):
    """«Municipalidad de Oberá» → Obera; el resto, Posadas (sede)."""
    bajo = sin_acentos(nombre_organismo.lower())
    for prefijo in ('municipalidad de ', 'municipio de '):
        if bajo.startswith(prefijo):
            localidad = sin_acentos(nombre_organismo[len(prefijo):].strip())
            if localidad.lower() not in ('misiones', ''):
                return Municipio.objects.get_or_create(nombre=localidad)[0]
    return Municipio.objects.get_or_create(nombre='Posadas')[0]


def modalidad_para(texto):
    """Virtual si el link habla de «online», «en línea», «digital»…"""
    bajo = sin_acentos(texto.lower())
    if any(p in bajo for p in ('en linea', 'online', 'digital', 'virtual')):
        return 'virtual'
    return 'presencial'
