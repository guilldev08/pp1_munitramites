"""
Carga los datos iniciales del proyecto en Firebird.

    docker compose exec web python manage.py cargar_datos

Es idempotente: se puede correr las veces que haga falta sin duplicar nada.
"""

from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from munitramites.models import (
    Consulta, Municipio, Organismo, Requisito, Tema, Tramite,
)


# El combo viejo del modelo usaba claves sin acento; el catálogo guarda
# el rótulo (lo que se ve en el formulario y en las fichas).
TEMAS = {'Documentacion': 'Documentación', 'Transito': 'Tránsito'}

# Los 7 temas del `choices` original: los crea la migración 0004, pero
# acá se aseguran de existir por si la base se vació (catálogo, no datos).
TEMAS_BASE = (
    'Documentacion', 'Transito', 'Comercio', 'Seguridad',
    'Salud', 'Impuestos', 'Vivienda',
)


def _tema(clave):
    """Fila de Tema para la clave histórica del trámite (idempotente)."""
    return Tema.objects.get_or_create(nombre=TEMAS.get(clave, clave))[0]


MUNICIPIOS = [
    'Posadas', 'Obera', 'Eldorado', 'Puerto Iguazu', 'Apostoles',
    'Jardin America', 'San Vicente', 'Montecarlo', 'Puerto Rico',
]

ORGANISMOS = [
    ('Registro Civil de Misiones', 'Av. Mitre 1234, Posadas'),
    ('Direccion de Transito', 'Calle Colon 567, Posadas'),
    ('Direccion de Comercio', 'Av. Uruguay 890, Posadas'),
    ('Policia de Misiones', 'Av. Corrientes 2345, Posadas'),
    ('Ministerio de Salud Publica', 'Calle Buenos Aires 678, Posadas'),
    ('Rentas de Misiones', 'Av. Roque Perez 1500, Posadas'),
    ('Direccion de Catastro', 'Calle San Martin 321, Posadas'),
]

# (titulo, tema, modalidad, municipio, organismo, destacado,
#  descripcion, enlace_turnos, enlace_oficial, requisitos)
TRAMITES = [
    (
        'Renovacion de DNI', 'Documentacion', 'presencial',
        'Posadas', 'Registro Civil de Misiones', True,
        'Tramite para la renovacion del Documento Nacional de Identidad '
        'ante el Registro Civil de la Provincia de Misiones.',
        'https://www.argentina.gob.ar/interior/renovacion-dni', '',
        [
            'DNI anterior (original)',
            'Partida de nacimiento actualizada',
            'Comprobante de domicilio (no mayor a 3 meses)',
            'Abonar la tasa correspondiente',
        ],
    ),
    (
        'Licencia Nacional de Conducir', 'Transito', 'presencial',
        'Posadas', 'Direccion de Transito', True,
        'Obtencion o renovacion de la Licencia Nacional de Conducir '
        'para vehiculos particulares y profesionales.',
        'https://www.posadas.gob.ar/turnos-licencia', '',
        [
            'DNI vigente',
            'Certificado de grupo sanguineo',
            'Examen psicofisico aprobado',
            'Curso teorico-practico aprobado',
            'Abonar arancel municipal',
        ],
    ),
    (
        'Partida de Nacimiento', 'Documentacion', 'virtual',
        'Posadas', 'Registro Civil de Misiones', True,
        'Solicitud de partida de nacimiento a traves del sistema virtual '
        'del Registro Civil de Misiones.',
        '', 'https://www.registrocivil.misiones.gob.ar',
        [
            'DNI del solicitante',
            'Datos completos de la persona (nombre, fecha de nacimiento)',
            'Abonar tasa provincial (si aplica)',
        ],
    ),
    (
        'Habilitacion Comercial', 'Comercio', 'mixta',
        'Obera', 'Direccion de Comercio', True,
        'Tramite para obtener la habilitacion comercial municipal '
        'para nuevos negocios en la ciudad de Obera.',
        '', '',
        [
            'DNI del titular',
            'Constancia de CUIT/CUIL',
            'Contrato de locacion o titulo de propiedad del local',
            'Certificado de factibilidad tecnica',
            'Abonar tasa municipal de habilitacion',
        ],
    ),
    (
        'Certificado de Antecedentes Penales', 'Seguridad', 'virtual',
        'Posadas', 'Policia de Misiones', False,
        'Obtencion del certificado de antecedentes penales provincial '
        'emitido por la Policia de Misiones.',
        '', 'https://www.policiamisiones.gob.ar/antecedentes',
        [
            'DNI vigente',
            'Completar formulario web',
            'Abonar tasa provincial',
        ],
    ),
    (
        'Certificado de Salud', 'Salud', 'presencial',
        'Eldorado', 'Ministerio de Salud Publica', False,
        'Tramite para obtener el certificado de buena salud requerido '
        'para diversas gestiones administrativas y laborales.',
        '', '',
        [
            'DNI vigente',
            'Carnet de vacunacion actualizado',
            'Asistir al centro de salud asignado',
        ],
    ),
    (
        'Inscripcion en Ingresos Brutos', 'Impuestos', 'virtual',
        'Posadas', 'Rentas de Misiones', False,
        'Inscripcion en el impuesto provincial sobre los Ingresos Brutos '
        'para contribuyentes de la provincia de Misiones.',
        '', 'https://www.rentas.misiones.gob.ar',
        [
            'DNI del titular',
            'Constancia de CUIT',
            'Constancia de domicilio fiscal',
            'Completar formulario F-400',
        ],
    ),
    (
        'Tramite de Titulo de Propiedad', 'Vivienda', 'presencial',
        'Puerto Iguazu', 'Direccion de Catastro', False,
        'Tramite de regularizacion dominial y obtencion de titulo de '
        'propiedad ante la Direccion de Catastro de Misiones.',
        '', '',
        [
            'DNI del titular',
            'Escritura o boleto de compraventa',
            'Plano de mensura aprobado',
            'Certificado de libre deuda municipal',
            'Abonar tasas catastrales',
        ],
    ),
]

# (tipo, asunto, contenido, tramite, fecha, estado)
CONSULTAS = [
    (
        'consulta',
        'Horarios de atencion del Registro Civil',
        'Buenos dias, quisiera saber los horarios de atencion del '
        'Registro Civil en Posadas para renovar el DNI. Gracias.',
        'Renovacion de DNI', '2026-09-15T10:30:00', 'pendiente',
    ),
    (
        'sugerencia',
        'Agregar tramites de turismo',
        'Seria util agregar tramites relacionados con turismo, como '
        'habilitaciones de alojamientos y guias turisticos.',
        None, '2026-09-14T15:45:00', 'pendiente',
    ),
    (
        'consulta',
        'Licencia para extranjeros',
        'Soy residente de Brasil y quisiera saber si puedo tramitar '
        'la licencia de conducir en Misiones.',
        'Licencia Nacional de Conducir', '2026-09-16T08:20:00', 'respondido',
    ),
]


class Command(BaseCommand):
    help = 'Carga municipios, organismos, temas, tramites, requisitos y consultas.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Municipios -------------------------------------------------------
        for nombre in MUNICIPIOS:
            Municipio.objects.get_or_create(nombre=nombre)
        self.stdout.write(f'  Municipios:      {Municipio.objects.count()}')

        # Organismos -------------------------------------------------------
        for nombre, direccion in ORGANISMOS:
            Organismo.objects.get_or_create(
                nombre=nombre, defaults={'direccion': direccion}
            )
        self.stdout.write(f'  Organismos:      {Organismo.objects.count()}')

        # Temas -------------------------------------------------------
        for clave in TEMAS_BASE:
            _tema(clave)
        self.stdout.write(f'  Temas:           {Tema.objects.count()}')

        # Tramites + requisitos -------------------------------------------
        creados = 0
        for (titulo, tema, modalidad, muni, org, destacado,
             descripcion, enlaces_turnos, enlace_oficial, reqs) in TRAMITES:
            tramite, created = Tramite.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'tema': _tema(tema),
                    'modalidad': modalidad,
                    'municipio': Municipio.objects.get(nombre=muni),
                    'organismo': Organismo.objects.get(nombre=org),
                    'descripcion': descripcion,
                    'enlace_turnos': enlaces_turnos,
                    'enlace_oficial': enlace_oficial,
                    'destacado': destacado,
                },
            )
            if created:
                creados += 1
                for i, req in enumerate(reqs, start=1):
                    Requisito.objects.create(
                        tramite=tramite, descripcion=req, orden=i
                    )
        self.stdout.write(
            f'  Tramites:        {Tramite.objects.count()} ({creados} nuevos)'
        )
        self.stdout.write(f'  Requisitos:      {Requisito.objects.count()}')

        # Consultas --------------------------------------------------------
        for (tipo, asunto, contenido, tramite_titulo, fecha, estado) in CONSULTAS:
            obj, created = Consulta.objects.get_or_create(
                asunto=asunto,
                defaults={
                    'tipo': tipo,
                    'contenido': contenido,
                    'estado': estado,
                    'tramite': (
                        Tramite.objects.filter(titulo=tramite_titulo).first()
                        if tramite_titulo else None
                    ),
                },
            )
            if created:
                # fecha es auto_now_add: hay que forzarla aparte, y con
                # timezone para que no avise Django (USE_TZ=True)
                dt = timezone.make_aware(datetime.fromisoformat(fecha))
                Consulta.objects.filter(pk=obj.pk).update(fecha=dt)

        self.stdout.write(f'  Consultas:       {Consulta.objects.count()}')
        self.stdout.write(self.style.SUCCESS('\nDatos cargados OK.'))
