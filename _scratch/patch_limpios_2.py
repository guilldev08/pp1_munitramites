# -*- coding: utf-8 -*-
"""Segunda pasada de ajustes de contenido."""

from munitramites.models import Requisito, Tramite

CAMBIOS = [
    ('Carnet sanitario', 'Foto digital', 'Foto digital del solicitante'),
    (
        'Solicitud de poda de arbolado urbano',
        'Operativo integral de poda o podador urbano artesanal inscripto',
        'Solicitud de operativo integral de poda o de podador urbano artesanal inscripto',
    ),
    (
        'Licencia de conducir por primera vez para menores de 16 y 17 años',
        'Presencia de los padres',
        'Presencia de ambos padres',
    ),
    (
        'Cambio de titularidad del servicio de agua',
        'Casos particulares: certificado de adjudicación, contrato de comodato, cesión de derechos, contrato de alquiler u otros',
        'Casos particulares: certificado de adjudicación, contrato de comodato, cesión de derechos o contrato de alquiler',
    ),
    (
        'Baja del servicio eléctrico',
        'Conexión sin deuda (no excluyente)',
        'Conexión sin deuda, no excluyente',
    ),
    (
        'Inscripción tardía administrativa de nacimiento',
        'Documentación complementaria que indique la delegación',
        'Documentación complementaria',
    ),
]

for titulo, viejo, nuevo in CAMBIOS:
    qs = Requisito.objects.filter(tramite__titulo=titulo, descripcion=viejo)
    if qs.count() != 1:
        raise SystemExit(f'{titulo}: se esperaba 1 coincidencia, hay {qs.count()}')
    qs.update(descripcion=nuevo)
    print(f'Actualizado: {titulo}')

TITULO = 'Habilitación de servicio de radiodiagnóstico y equipos emisores de radiaciones'
NUEVOS = [
    'Nota modelo de solicitud dirigida a la Dirección de Saneamiento Ambiental',
    'Formulario para rayos X convencional, arco en C, odontológico, panorámico, unidad móvil, medicina preocupacional o resonancia magnética, según el equipo',
    'Formulario para medicina nuclear, radioterapia, acelerador lineal, braquiterapia, PET/CT, cámara gamma, láser/IPL o rayos X industrial, según el equipo',
    'Documentación técnica, profesional y de seguridad que exige el formulario correspondiente',
    'Cumplimiento de la Ley Nacional 17.557 y la Ley Provincial XVII N° 58, Cap. IX, Art. 38, inc. 19',
]
tramite = Tramite.objects.get(titulo=TITULO)
tramite.requisitos.all().delete()
Requisito.objects.bulk_create([
    Requisito(tramite=tramite, descripcion=texto, orden=orden)
    for orden, texto in enumerate(NUEVOS, 1)
])
print(f'Reemplazado: {TITULO} ({len(NUEVOS)} requisitos)')
print('Listo.')
