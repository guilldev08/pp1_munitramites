# -*- coding: utf-8 -*-
"""Tercera pasada: separa ítems combinados y ajusta redacción."""

import importlib
import sys
from pathlib import Path

from django.conf import settings

sys.path.insert(0, str(Path(settings.BASE_DIR) / '_scratch'))

from munitramites.models import Requisito, Tramite  # noqa: E402

REEMPLAZAR = {
    'rc': [
        'Inscripción de matrimonio',
        'Matrimonio de extranjeros no residentes',
    ],
}

CAMBIOS = [
    (
        'Permiso de viaje para menores dentro del país',
        'Libreta de matrimonio con nacimiento asentado o testimonio judicial de adopción como alternativa para acreditar el vínculo',
        'Alternativa para acreditar el vínculo: libreta de matrimonio con nacimiento asentado o testimonio judicial de adopción',
    ),
    (
        'Tarifa Social provincial',
        'Sin automotores de hasta 10 años de antigüedad, aeronaves o embarcaciones de lujo',
        'Sin automotores de menos de 10 años de antigüedad, aeronaves o embarcaciones de lujo',
    ),
    (
        'Solicitud de conexión domiciliaria de agua y cloaca',
        'Comprobante de pago de derechos de conexión, abonado en tesorería o banco habilitado',
        'Comprobante de pago de derechos de conexión en tesorería o banco habilitado',
    ),
]

for modulo_nombre, titulos in REEMPLAZAR.items():
    modulo = importlib.import_module(f'limpios.{modulo_nombre}')
    for titulo in titulos:
        tramite = Tramite.objects.get(titulo=titulo)
        requisitos = modulo.REQUISITOS[titulo]
        tramite.requisitos.all().delete()
        Requisito.objects.bulk_create([
            Requisito(tramite=tramite, descripcion=texto, orden=orden)
            for orden, texto in enumerate(requisitos, 1)
        ])
        print(f'Reemplazado: {titulo} ({len(requisitos)})')

for titulo, viejo, nuevo in CAMBIOS:
    qs = Requisito.objects.filter(tramite__titulo=titulo, descripcion=viejo)
    if qs.count() != 1:
        raise SystemExit(f'{titulo}: se esperaba 1 coincidencia, hay {qs.count()}')
    qs.update(descripcion=nuevo)
    print(f'Actualizado: {titulo}')

print('Listo.')
