"""Funciones de ayuda para armar los datos de prueba una sola vez."""

from django.contrib.auth.models import User
from django.test import TestCase as _TestCase, override_settings

from munitramites.models import Municipio, Organismo, Perfil, Requisito, Tramite
from munitramites.services.chatbot import indexar

# CHATBOT_LLM sin proveedor: en los tests el asistente redacta con la
# plantilla local y NUNCA se abre una conexión con Ollama. Así la suite
# anda igual con el contenedor apagado y nadie espera los segundos de CPU
# del modelo. Los tests del LLM lo reactivan con self.settings(...).
CHATBOT_LLM_APAGADO = {
    'proveedor': '',
    'api_key': '',
    'modelo': '',
    'base_url': '',
    'timeout': 20,
}


class TestCase(_TestCase):
    """TestCase de Django con dos ajustes propios.

    Vacía el índice del chatbot antes y después de cada test: el índice vive
    en memoria y los tests revierten la base, así que si no se limpia, un
    test podría ver los trámites de otro.

    Además deja el LLM apagado (ver CHATBOT_LLM_APAGADO): los tests dicen
    lo que debe pasar, no lo que diga un modelo. Ese override va en
    setUpClass y no en setUp porque varias subclases redefinen setUp sin
    llamar a super().
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._llm_apagado = override_settings(CHATBOT_LLM=CHATBOT_LLM_APAGADO)
        cls._llm_apagado.enable()

    @classmethod
    def tearDownClass(cls):
        cls._llm_apagado.disable()
        super().tearDownClass()

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


def tramite(titulo='Renovacion de DNI', tema='Documentacion',
            modalidad='presencial', **kwargs):
    """Trámite de prueba con un requisito cargado."""
    datos = {
        'titulo': titulo,
        'tema': tema,
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


def administrador(username='admin', password='ClaveSegura123'):
    """Rol Administrador del documento: entra al panel y gestiona todo.

    En Django eso es `is_staff` + `is_superuser` (los permisos de cada tabla
    vienen dados por el superusuario; si algún día hace falta un rol intermedio,
    se usan los grupos y `User.user_permissions`).
    """
    user = User.objects.create_superuser(
        username=username, email=f'{username}@munitramites.test',
        password=password,
    )
    Perfil.objects.create(user=user, dni='99111222')
    return user
