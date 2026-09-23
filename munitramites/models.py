"""
Modelos. >>> ACÁ VAN LAS TABLAS DE FIREBIRD <<<

Todavia no hay modelos propios: la SPA muestra datos hardcodeados en el
bundle de JavaScript, no de la base.

Cuando quieras que el panel lea/escriba de verdad:

  1. Crear la clase aqui
  2. docker compose exec web python manage.py makemigrations munitramites
  3. docker compose exec web python manage.py migrate
  4. Registrarla en munitramites/admin.py para verla en /django-admin/
  5. Exponerla en una API (o renderizarla desde una vista en views.py)

Ejemplo:

    class Tramite(models.Model):
        nombre = models.CharField(max_length=200)
        organismo = models.CharField(max_length=200)
        creado = models.DateTimeField(auto_now_add=True)

        class Meta:
            verbose_name_plural = 'tramites'

        def __str__(self):
            return self.nombre
"""

from django.db import models  # noqa: F401
