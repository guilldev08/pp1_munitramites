# -*- coding: utf-8 -*-
"""Valida los módulos de requisitos limpios antes de aplicarlos.

Se ejecuta con:
    docker compose exec -T web python manage.py shell < _scratch/validar_limpios.py
"""

import importlib
import re
import sys
from pathlib import Path

from django.conf import settings

sys.path.insert(0, str(Path(settings.BASE_DIR) / '_scratch'))

from munitramites.models import Requisito, Tramite  # noqa: E402

MODULOS = [
    'policia', 'samsa', 'obera', 'iguazu', 'pj', 'energia',
    'atm', 'salud', 'iprodha', 'posadas', 'rc',
]

nuevos = {}
titulos = {}
for nombre in MODULOS:
    modulo = importlib.import_module(f'limpios.{nombre}')
    nuevos.update(modulo.REQUISITOS)
    titulos.update(getattr(modulo, 'TITULOS', {}))

db_titulos = set(Tramite.objects.values_list('titulo', flat=True))
map_titulos = set(nuevos)

print(f'Módulos: {len(MODULOS)}')
print(f'Trámites en módulos: {len(map_titulos)}')
print(f'Trámites en base: {len(db_titulos)}')
print(f'Requisitos nuevos: {sum(len(v) for v in nuevos.values())}')
print(f'Requisitos actuales: {Requisito.objects.count()}')

faltan_en_db = sorted(map_titulos - db_titulos)
faltan_en_modulos = sorted(db_titulos - map_titulos)
if faltan_en_db:
    print('\nTÍTULOS DE MÓDULO QUE NO ESTÁN EN LA BASE')
    for t in faltan_en_db:
        print(f'  - {t}')
if faltan_en_modulos:
    print('\nTÍTULOS DE LA BASE SIN MÓDULO LIMPIO')
    for t in faltan_en_modulos:
        print(f'  - {t}')

patrones = {
    'código SR': re.compile(r'\bSR[-\s]?\d+', re.I),
    'formulario numerado': re.compile(r'\bFormulario\s+\d+', re.I),
    'anexo': re.compile(r'\bAnexo\b', re.I),
    'DJ': re.compile(r'\bDJ-', re.I),
    'URL': re.compile(r'https?://', re.I),
    'correo': re.compile(r'@'),
    'ID interno': re.compile(r'\bID\b'),
}
alertas = []
for titulo, requisitos in nuevos.items():
    if not requisitos:
        alertas.append((titulo, 'SIN REQUISITOS'))
    vistos = set()
    for i, texto in enumerate(requisitos, 1):
        if not texto.strip():
            alertas.append((titulo, f'{i}: vacío'))
        if len(texto) > 300:
            alertas.append((titulo, f'{i}: {len(texto)} caracteres'))
        if texto != texto.strip():
            alertas.append((titulo, f'{i}: espacios al inicio o al final'))
        if texto.endswith('.'):
            alertas.append((titulo, f'{i}: termina en punto'))
        if texto and not texto[0].isupper():
            alertas.append((titulo, f'{i}: empieza en minúscula'))
        if texto in vistos:
            alertas.append((titulo, f'{i}: duplicado'))
        vistos.add(texto)
        for etiqueta, patron in patrones.items():
            if patron.search(texto):
                alertas.append((titulo, f'{i}: {etiqueta} -> {texto}'))

if alertas:
    print(f'\nALERTAS ({len(alertas)})')
    for titulo, detalle in alertas:
        print(f'  - {titulo}: {detalle}')
else:
    print('\nSin alertas de formato.')

largos = sorted(
    ((len(texto), titulo, texto) for titulo, reqs in nuevos.items() for texto in reqs),
    reverse=True,
)[:15]
print('\nREQUISITOS MÁS LARGOS')
for largo, titulo, texto in largos:
    print(f'  {largo:3} · {titulo}: {texto[:110]}')

print('\nCONTEO POR TRÁMITE')
for titulo in sorted(nuevos):
    print(f'  {len(nuevos[titulo]):2} · {titulo}')
