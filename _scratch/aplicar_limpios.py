# -*- coding: utf-8 -*-
"""Aplica los requisitos limpios a la base local.

Se ejecuta con:
    docker compose exec -T web python manage.py shell -c "exec(open('_scratch/aplicar_limpios.py', encoding='utf-8').read())"
"""

import importlib
import sys
from pathlib import Path

from django.conf import settings
from django.db import transaction

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
if set(nuevos) != db_titulos:
    faltan = sorted(set(nuevos) - db_titulos)
    sobran = sorted(db_titulos - set(nuevos))
    raise SystemExit(f'No coinciden los títulos. Faltan: {faltan}. Sobran: {sobran}')

antes = Requisito.objects.count()
aplicados = 0
renombrados = 0

with transaction.atomic():
    for viejo, requisitos in nuevos.items():
        tramite = Tramite.objects.get(titulo=viejo)
        tramite.requisitos.all().delete()
        Requisito.objects.bulk_create([
            Requisito(tramite=tramite, descripcion=texto, orden=orden)
            for orden, texto in enumerate(requisitos, 1)
        ])
        aplicados += len(requisitos)
        if viejo in titulos:
            tramite.titulo = titulos[viejo]
            tramite.save(update_fields=['titulo', 'actualizado'])
            renombrados += 1

despues = Requisito.objects.count()
print(f'Requisitos antes: {antes}')
print(f'Requisitos aplicados: {aplicados}')
print(f'Requisitos después: {despues}')
print(f'Títulos renombrados: {renombrados}')

vacios = [
    t.titulo for t in Tramite.objects.all()
    if not t.requisitos.exists()
]
print(f'Trámites sin requisitos: {len(vacios)}')
for titulo in vacios:
    print(f'  - {titulo}')

largos = Requisito.objects.filter(descripcion__gt='').order_by('-id')[:5]
print('Muestra:')
for r in largos:
    print(f'  {r.tramite.titulo} / {r.orden}: {r.descripcion}')
