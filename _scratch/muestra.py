# -*- coding: utf-8 -*-
from munitramites.models import Tramite

TITULOS = [
    'Alta, modificación o cese de actividades',
    'Cambio de titular o contribuyente inmobiliario',
    'Exclusiones, compensaciones y devoluciones',
    'Habilitación de servicio de radiodiagnóstico y equipos emisores de radiaciones',
    'Inscripción de producto domisanitario',
    'Inscripción de matrimonio',
    'Matrimonio de extranjeros no residentes',
    'Permiso de viaje para menores dentro del país',
    'Habilitación e inscripción o traslado de comercio',
    'Renovación de licencia de conducir',
    'Cambio de titularidad del servicio de agua',
    'Solicitud de conexión domiciliaria de agua y cloaca',
    'Tarifa Social provincial',
    'Rúbrica de libros societarios',
]

for titulo in TITULOS:
    tramite = Tramite.objects.get(titulo=titulo)
    print(f'## {tramite.titulo}')
    for requisito in tramite.requisitos.all():
        print(f'{requisito.orden}. {requisito.descripcion}')
    print()
