"""
Modelos. >>> ACÁ VAN LAS TABLAS DE FIREBIRD <<<

Estructura del dominio:

    Municipio ──┐
                ├──► Tramite ──► Requisito
    Organismo ──┘        ├──► Enlace  (botones de la ficha, los edita el admin)
    Tema ────────────────┘
                          └──► Consulta ──► User ──► Perfil (DNI)

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
    ocupacion = models.CharField(
        'Área de acción',
        max_length=200,
        blank=True,
        default='',
        help_text='Rubro o materia que agrupa, ej.: «Registro Civil», «Tránsito».',
    )

    class Meta:
        verbose_name = 'Organismo'
        verbose_name_plural = 'Organismos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Tema(models.Model):
    """Tema de un tramite, cargado desde el panel.

    Antes era un `choices` fijo en el modelo (Documentación, Tránsito, …):
    ahora es una tabla, así el administrador carga los que quiera sin
    tocar código. Los 7 iniciales los crea la migración 0004.
    """

    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        verbose_name = 'Tema'
        verbose_name_plural = 'Temas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Tramite(models.Model):
    """Un tramite publico que puede realizar un ciudadano."""

    class Modalidad(models.TextChoices):
        PRESENCIAL = 'presencial', 'Presencial'
        VIRTUAL = 'virtual', 'Virtual'
        MIXTA = 'mixta', 'Mixta'

    titulo = models.CharField(max_length=200)
    tema = models.ForeignKey(Tema, on_delete=models.PROTECT, related_name='tramites')
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


class Enlace(models.Model):
    """Boton de enlace oficial que se muestra en la ficha de un tramite.

    El admin carga el TEXTO del boton (nombre) y la URL, asi cada organismo
    decide como se llama el boton («Pedir turno», «Trámites en línea», …).
    """

    tramite = models.ForeignKey(
        Tramite, on_delete=models.CASCADE, related_name='enlaces'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Texto del boton, ej.: «Pedir turno» o «Sitio del organismo».',
    )
    url = models.URLField(help_text='URL completa, ej.: https://ejemplo.gob.ar/…')
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Enlace oficial'
        verbose_name_plural = 'Enlaces oficiales'
        ordering = ['orden', 'id']

    def __str__(self):
        return f'{self.nombre} → {self.url}'


class Perfil(models.Model):
    """Datos personales de la cuenta y su rol en el sitio.

    El documento pide almacenar nombre, apellido, DNI y email. Nombre,
    apellido y email ya viven en `User` (se cargan en el registro); el DNI
    vive aca, en uno a uno con la cuenta.

    El `rol` tambien vive acá y es la única fuente de verdad de quién
    gestiona qué. Los tres roles son ACUMULATIVOS (el administrador puede
    todo lo del administrativo y este, todo lo del corriente) y
    `is_staff` se mantiene sincronizado con el rol para que las reglas de
    acceso al /admin/ de Django sigan andando: ninguno de los tres entra
    ahi — el /admin/ es del superusuario (ver middleware.py).
    """

    class Rol(models.TextChoices):
        CORRIENTE = 'corriente', 'Corriente'
        ADMINISTRATIVO = 'administrativo', 'Administrativo'
        ADMINISTRADOR = 'administrador', 'Administrador'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil'
    )
    dni = models.CharField(
        'DNI',
        max_length=12,
        blank=True,
        default='',
        help_text='Sin puntos ni espacios, ej.: 12345678.',
    )
    rol = models.CharField(
        'rol',
        max_length=20,
        choices=Rol.choices,
        default=Rol.CORRIENTE,
        help_text=(
            'Corriente: ve trámites y envía consultas. '
            'Administrativo: además responde consultas y edita trámites y temas. '
            'Administrador: además gestiona las cuentas.'
        ),
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        return f'{self.user.username} — DNI {self.dni or "sin cargar"}'


def gestiona_cuentas(user):
    """¿Esta cuenta puede gestionar cuentas ajenas (/panel/usuarios/)?

    Solo el rol «administrador» y el superusuario, que está fuera de los
    tres roles: es la única cuenta que entra al /admin/ de Django.
    """
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        # Corriente: corto acá para no pegar una consulta por perfil
        return False
    perfil = getattr(user, 'perfil', None)
    return perfil is not None and perfil.rol == Perfil.Rol.ADMINISTRADOR


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
