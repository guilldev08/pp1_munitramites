"""Funciones de ayuda para armar los datos de prueba una sola vez."""

from django.contrib.auth.models import User
from django.test import TestCase as _TestCase

from munitramites.models import (
    Municipio, Organismo, Perfil, Requisito, Tema, Tramite,
)
from munitramites.services.chatbot import indexar


class TestCase(_TestCase):
    """TestCase de Django con una particularidad propia.

    Vacía el índice del chatbot antes y después de cada test: el índice vive
    en memoria y los tests revierten la base, así que si no se limpia, un
    test podría ver los trámites de otro.
    """

    def setUp(self):
        super().setUp()
        indexar.invalidar()

    def tearDown(self):
        indexar.invalidar()
        super().tearDown()


def municipio(nombre='Posadas'):
    obj, _ = Municipio.objects.get_or_create(nombre=nombre)
    return obj


def organismo(nombre='Registro Civil de Misiones', direccion='Av. Mitre 1234'):
    obj, _ = Organismo.objects.get_or_create(
        nombre=nombre, defaults={'direccion': direccion}
    )
    return obj


def tramite(titulo='Renovacion de DNI', tema='Documentación',
            modalidad='presencial', **kwargs):
    """Trámite de prueba con un requisito cargado."""
    datos = {
        'titulo': titulo,
        'tema': Tema.objects.get_or_create(nombre=tema)[0],
        'modalidad': modalidad,
        'municipio': municipio(),
        'organismo': organismo(),
        'descripcion': 'Tramite de prueba para los tests de aceptacion.',
        'destacado': False,
        'activo': True,
    }
    datos.update(kwargs)
    obj, creado = Tramite.objects.get_or_create(titulo=titulo, defaults=datos)
    if creado:
        Requisito.objects.get_or_create(
            tramite=obj, orden=1,
            defaults={'descripcion': 'DNI en vigor y formulario completado'},
        )
    return obj


def ciudadano(username='ana', dni='28111222', password='ClaveSegura123', **kwargs):
    """Usuario común con su perfil (como si se hubiera registrado)."""
    datos = {
        'email': f'{username}@munitramites.test',
        'first_name': 'Ana',
        'last_name': 'Prueba',
    }
    datos.update(kwargs)
    user = User.objects.create_user(username=username, password=password, **datos)
    Perfil.objects.create(user=user, dni=dni)
    return user


def administrador(username='admin', password='ClaveSegura123', **kwargs):
    """Rol «Usuario administrador»: gestiona TODO el panel, cuentas incluidas.

    En Django es `is_staff=True` SIN `is_superuser` (el /admin/ de Django
    queda para el superusuario; ver middleware.py) y el rol vive en
    `Perfil.rol`, que se mantiene sincronizado con `is_staff`.
    """
    datos = {
        'email': f'{username}@munitramites.test',
        'is_staff': True,
    }
    datos.update(kwargs)
    user = User.objects.create_user(username=username, password=password, **datos)
    Perfil.objects.create(user=user, dni='99111222', rol=Perfil.Rol.ADMINISTRADOR)
    return user


def administrativo(username='gestor', password='ClaveSegura123', **kwargs):
    """Rol «Usuario administrativo»: trámites, consultas y temas; NO cuentas."""
    datos = {
        'email': f'{username}@munitramites.test',
        'is_staff': True,
    }
    datos.update(kwargs)
    user = User.objects.create_user(username=username, password=password, **datos)
    Perfil.objects.create(user=user, dni='99111223', rol=Perfil.Rol.ADMINISTRATIVO)
    return user


def superusuario(username='jefe', password='ClaveSegura123'):
    """La ÚNICA cuenta de superusuario (la regla la impone `senales.py`).

    Ojo: solo puede existir UNA por base de datos — si un test necesita
    otra cuenta, que use `ciudadano()` o `administrador()`.
    """
    user = User.objects.create_superuser(
        username=username, email=f'{username}@munitramites.test',
        password=password,
    )
    Perfil.objects.create(user=user, dni='99111222')
    return user
