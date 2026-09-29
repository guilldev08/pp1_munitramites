from django.apps import AppConfig


class MunitramitesConfig(AppConfig):
    """Identidad de la app. El nombre del paquete ES el nombre del esquema:

    `name = 'munitramites'` hace que Django use `munitramites_*` como
    prefijo de tabla en Firebird (`munitramites_tramite`,
    `munitramites_consulta`, …) y registre las migraciones con el mismo
    label. Si renombras la carpeta, cambia esto aca y en INSTALLED_APPS.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'munitramites'
    verbose_name = 'Munitramites'

    def ready(self):
        # El índice del chatbot se invalida solo cuando cambian los datos.
        from .services.chatbot import indexar

        indexar.conectar_senales()
