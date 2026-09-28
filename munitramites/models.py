"""
Modelos. >>> ACÁ VAN LAS TABLAS DE FIREBIRD <<<

Estructura del dominio:

    Municipio ──┐
                ├──► Tramite ──► Requisito
    Organismo ──┘        │
                         └──► Consulta ──► User

Todas las tablas viven en Firebird. Después de tocar este archivo:

    docker compose exec web python manage.py makemigrations munitramites
    docker compose exec web python manage.py migrate
"""

from django.conf import settings
from django.db import models


class Municipio(models.Model):
    """Municipio de la provincia de Misiones."""

    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Organismo(models.Model):
    """Organismo publico responsable de los tramites."""

    nombre = models.CharField(max_length=200, unique=True)
    direccion = models.CharField(max_length=200)

    class Meta:
        verbose_name = 'Organismo'
        verbose_name_plural = 'Organismos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Tramite(models.Model):
    """Un tramite publico que puede realizar un ciudadano."""

    class Tema(models.TextChoices):
        DOCUMENTACION = 'Documentacion', 'Documentación'
        TRANSITO = 'Transito', 'Tránsito'
        COMERCIO = 'Comercio', 'Comercio'
        SEGURIDAD = 'Seguridad', 'Seguridad'
        SALUD = 'Salud', 'Salud'
        IMPUESTOS = 'Impuestos', 'Impuestos'
        VIVIENDA = 'Vivienda', 'Vivienda'

    class Modalidad(models.TextChoices):
        PRESENCIAL = 'presencial', 'Presencial'
        VIRTUAL = 'virtual', 'Virtual'
        MIXTA = 'mixta', 'Mixta'

    titulo = models.CharField(max_length=200)
    tema = models.CharField(max_length=20, choices=Tema.choices)
    modalidad = models.CharField(max_length=20, choices=Modalidad.choices)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='tramites'
    )
    organismo = models.ForeignKey(
        Organismo, on_delete=models.PROTECT, related_name='tramites'
    )
    descripcion = models.TextField()
    enlace_turnos = models.URLField(blank=True, default='')
    enlace_oficial = models.URLField(blank=True, default='')
    destacado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trámite'
        verbose_name_plural = 'Trámites'
        ordering = ['-destacado', 'titulo']

    def __str__(self):
        return self.titulo

    @property
    def temas_display(self):
        return self.get_tema_display()

    @property
    def modalidad_display(self):
        return self.get_modalidad_display()


class Requisito(models.Model):
    """Un requisito concreto de un tramite (1 a N)."""

    tramite = models.ForeignKey(
        Tramite, on_delete=models.CASCADE, related_name='requisitos'
    )
    descripcion = models.CharField(max_length=300)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Requisito'
        verbose_name_plural = 'Requisitos'
        ordering = ['orden', 'id']
        unique_together = [('tramite', 'orden')]

    def __str__(self):
        return f'{self.tramite} — {self.descripcion[:40]}'


class Consulta(models.Model):
    """Consulta o sugerencia enviada por un ciudadano."""

    class Tipo(models.TextChoices):
        CONSULTA = 'consulta', 'Consulta'
        SUGERENCIA = 'sugerencia', 'Sugerencia'
        RECLAMO = 'reclamo', 'Reclamo'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        RESPONDIDO = 'respondido', 'Respondido'
        CERRADO = 'cerrado', 'Cerrado'

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.CONSULTA)
    asunto = models.CharField(max_length=200)
    contenido = models.TextField()
    tramite = models.ForeignKey(
        Tramite, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consultas',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='consultas',
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    respuesta = models.TextField(blank=True, default='')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consulta'
        verbose_name_plural = 'Consultas'
        ordering = ['-fecha']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.asunto}'
