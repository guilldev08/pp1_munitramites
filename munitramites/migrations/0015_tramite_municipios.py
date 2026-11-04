# Migración de la SPEC «Formulario de creación de trámite» (2026-11):
#   1. agrega `Tramite.municipios` (M2M) para poder declarar más de un
#      municipio por trámite,
#   2. copia el municipio viejo (FK) de cada trámite a la relación nueva,
#      para que los datos existentes sigan apareciendo igual,
#   3. crea los 73 municipios de la lista de la SPEC (los cuatro que ya
#      estaban —Posadas, Oberá, Eldorado y Puerto Iguazú— quedan como están,
#      porque sus nombres ya coinciden con la lista).

from django.db import migrations, models

# Lista completa de la SPEC (se crea el que falte con get_or_create).
MUNICIPIOS = [
    'Alba Posse', 'Almafuerte', 'Apóstoles', 'Aristóbulo del Valle',
    'Arroyo del Medio', 'Azara', 'Bernardo de Irigoyen', 'Bonpland',
    'Caá Yarí', 'Campo Grande', 'Campo Ramón', 'Campo Viera', 'Candelaria',
    'Capioví', 'Caraguatay', 'Cerro Azul', 'Cerro Corá', 'Colonia Alberdi',
    'Colonia Aurora', 'Colonia Delicia', 'Colonia Polana', 'Colonia Victoria',
    'Colonia Wanda', 'Comandante Andresito', 'Concepción de la Sierra',
    'Corpus Christi', 'Dos Arroyos', 'Dos de Mayo', 'El Alcázar',
    'El Soberbio', 'Eldorado', 'Fachinal', 'Florentino Ameghino',
    'Garuhapé', 'Garupá', 'General Alvear', 'Gobernador López',
    'Gobernador Roca', 'Guaraní', 'Hipólito Yrigoyen', 'Itacaruaré',
    'Jardín América', 'Leandro N. Alem', 'Loreto', 'Los Helechos',
    'Mártires', 'Mojón Grande', 'Montecarlo', 'Oberá', 'Panambí', 'Posadas',
    'Profundidad', 'Puerto Esperanza', 'Puerto Iguazú', 'Puerto Libertad',
    'Puerto Piray', 'Puerto Rico', 'Ruiz de Montoya', 'Salto Encantado',
    'San Ignacio', 'San Javier', 'San José', 'San Pedro', 'San Vicente',
    'Santa Ana', 'Santa María', 'Santiago de Liniers', 'Tres Capones',
    '25 de Mayo',
]


def copiar_municipio_principal(apps, schema_editor):
    """Cada trámite queda asociado a su municipio principal (el FK viejo)."""
    Tramite = apps.get_model('munitramites', 'Tramite')
    for tramite in Tramite.objects.all():
        tramite.municipios.add(tramite.municipio_id)


def crear_municipios_de_la_lista(apps, schema_editor):
    Municipio = apps.get_model('munitramites', 'Municipio')
    creado = 0
    for nombre in MUNICIPIOS:
        _, fue_creado = Municipio.objects.get_or_create(nombre=nombre)
        if fue_creado:
            creado += 1
    print(f'\nMunicipios creados por la migración: {creado}')


class Migration(migrations.Migration):

    dependencies = [
        ('munitramites', '0014_consulta_fecha_edicion'),
    ]

    operations = [
        migrations.AddField(
            model_name='tramite',
            name='municipios',
            field=models.ManyToManyField(related_name='tramites_municipios', to='munitramites.municipio'),
        ),
        migrations.RunPython(
            copiar_municipio_principal, migrations.RunPython.noop
        ),
        migrations.RunPython(
            crear_municipios_de_la_lista, migrations.RunPython.noop
        ),
    ]
