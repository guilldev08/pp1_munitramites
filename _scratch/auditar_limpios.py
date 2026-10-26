# -*- coding: utf-8 -*-
"""Audita títulos, descripciones y requisitos ya aplicados."""

import re

from munitramites.models import Requisito, Tramite

patrones = {
    'código SR/SF': re.compile(r'\bS[RF][-\s]?\d+', re.I),
    'formulario numerado': re.compile(r'\bFormulario\s+\d+', re.I),
    'anexo': re.compile(r'\bAnexo\b', re.I),
    'DJ': re.compile(r'\bDJ-', re.I),
    'URL': re.compile(r'https?://', re.I),
    'correo': re.compile(r'@'),
    'ID interno': re.compile(r'\bID\b'),
    'verbo de proceso': re.compile(
        r'^(presentar|presentarse|abonar|completar|concurrir|ingresar|realizar|'
        r'solicitar|informar|firmar|acreditar|contar con|estar|tener|ser |poseer|'
        r'disponer|adjuntar|acompañar|indicar|detallar|seleccionar|consultar|'
        r'aguardar|esperar|recibir|iniciar|tramitar|gestionar|pedir)\b',
        re.I,
    ),
    'referencia a trámite': re.compile(
        r'\b(trámite|tramite|sistema|online|link|página web|sitio web)\b', re.I
    ),
}

print('=== TÍTULOS CON CÓDIGOS O REFERENCIAS ===')
for t in Tramite.objects.all():
    for etiqueta, patron in patrones.items():
        if patron.search(t.titulo):
            print(f'{etiqueta}: {t.titulo}')

print('\n=== DESCRIPCIONES CON CÓDIGOS, URLS O REFERENCIAS ===')
for t in Tramite.objects.all():
    for etiqueta, patron in patrones.items():
        if patron.search(t.descripcion):
            print(f'{etiqueta}: {t.titulo}')
            print(f'  {t.descripcion[:300]}')

print('\n=== REQUISITOS CON VERBOS O REFERENCIAS ===')
for r in Requisito.objects.select_related('tramite').all():
    for etiqueta, patron in patrones.items():
        if patron.search(r.descripcion):
            print(f'{etiqueta}: {r.tramite.titulo} / {r.orden}: {r.descripcion}')
