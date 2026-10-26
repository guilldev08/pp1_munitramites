# -*- coding: utf-8 -*-
"""Exporta los requisitos para auditar coherencia (script temporal)."""

import csv
import os
import re
import sys

import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'munitramites.settings')
django.setup()

from munitramites.models import Tramite  # noqa: E402

PATRONES = {
    'id': re.compile(r'\bID\b|#\s*\d+|\bc[oó]digo\s+\d+', re.I),
    'otro_tramite': re.compile(
        r'\btr[aá]mites?\b.*\b(?:id|n[uú]mero|n[°º]|siguiente|anterior|mencionad)'
        r'|\bver\s+tr[aá]mite|\bir\s+a\s+la\s+ficha|\bdesde\s+la\s+ficha',
        re.I,
    ),
    'navegacion': re.compile(
        r'\b(?:hacer\s+clic|click|link|enlace|p[aá]gina\s+web|sitio\s+web|'
        r'ingresar\s+a|acceder\s+a|descargar\s+desde|men[uú])\b',
        re.I,
    ),
    'formulario': re.compile(r'\b(?:formulario|planilla|anexo)\b', re.I),
    'sistema': re.compile(
        r'\b(?:sistema|plataforma|portal|app|aplicaci[oó]n|online|virtual)\b', re.I,
    ),
}

with open('/app/_scratch/requisitos_auditoria.tsv', 'w', encoding='utf-8', newline='') as archivo:
    writer = csv.writer(archivo, delimiter='\t')
    writer.writerow([
        'pk_tramite', 'organismo', 'tramite', 'orden', 'requisito', 'alertas',
    ])
    for tramite in (
        Tramite.objects.select_related('organismo')
        .prefetch_related('requisitos')
        .order_by('organismo__nombre', 'titulo')
    ):
        for requisito in tramite.requisitos.all().order_by('orden', 'pk'):
            alertas = [
                nombre for nombre, patron in PATRONES.items()
                if patron.search(requisito.descripcion)
            ]
            writer.writerow([
                tramite.pk,
                tramite.organismo.nombre,
                tramite.titulo,
                requisito.orden,
                requisito.descripcion,
                ','.join(alertas),
            ])

print('OK')
