from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('munitramites', '0008_alter_tramite_enlace_oficial_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enlace',
            name='url',
            field=models.URLField(
                help_text='URL completa, ej.: https://ejemplo.gob.ar/…',
                max_length=300,
            ),
        ),
    ]
