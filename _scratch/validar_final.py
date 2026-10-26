# -*- coding: utf-8 -*-
"""Validación final de la base cargada."""

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
}

errores = []
for t in Tramite.objects.all():
    reqs = list(t.requisitos.all())
    if not reqs:
        errores.append(f'{t.titulo}: sin requisitos')
    ordenes = [r.orden for r in reqs]
    if ordenes != list(range(1, len(reqs) + 1)):
        errores.append(f'{t.titulo}: orden discontinuo {ordenes}')
    vistos = set()
    for r in reqs:
        texto = r.descripcion
        if not texto.strip():
            errores.append(f'{t.titulo}: requisito vacío')
        if len(texto) > 300:
            errores.append(f'{t.titulo}: requisito de {len(texto)} caracteres')
        if texto.endswith('.'):
            errores.append(f'{t.titulo}: requisito termina en punto')
        if texto and not texto[0].isupper():
            errores.append(f'{t.titulo}: requisito empieza en minúscula')
        if texto in vistos:
            errores.append(f'{t.titulo}: requisito duplicado')
        vistos.add(texto)
        if patrones['verbo de proceso'].search(texto):
            errores.append(f'{t.titulo}: verbo de proceso -> {texto}')
        for etiqueta in ('código SR/SF', 'formulario numerado', 'anexo', 'DJ', 'URL', 'correo', 'ID interno'):
            if patrones[etiqueta].search(texto):
                errores.append(f'{t.titulo}: {etiqueta} -> {texto}')

print(f'Trámites: {Tramite.objects.count()}')
print(f'Requisitos: {Requisito.objects.count()}')
print(f'Promedio por trámite: {Requisito.objects.count() / max(Tramite.objects.count(), 1):.1f}')
print(f'Mínimo por trámite: {min(t.requisitos.count() for t in Tramite.objects.all())}')
print(f'Máximo por trámite: {max(t.requisitos.count() for t in Tramite.objects.all())}')

print('\nTÍTULOS CON CÓDIGOS O FORMATOS INTERNOS')
for t in Tramite.objects.all():
    for etiqueta, patron in patrones.items():
        if patron.search(t.titulo):
            print(f'  {etiqueta}: {t.titulo}')

print('\nDESCRIPCIONES CON CÓDIGOS O FORMATOS INTERNOS')
for t in Tramite.objects.all():
    for etiqueta in ('código SR/SF', 'formulario numerado', 'anexo', 'DJ', 'URL', 'correo', 'ID interno'):
        if patrones[etiqueta].search(t.descripcion):
            print(f'  {etiqueta}: {t.titulo}')

print('\nERRORES')
if errores:
    for error in errores:
        print(f'  - {error}')
else:
    print('  Ninguno.')
