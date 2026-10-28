"""
Registro de modelos en /admin/. >>> ACÁ SE HACEN VISIBLES <<<
Solo aparece en el panel lo que esté registrado acá.

OJO: desde la feature del panel propio, /admin/ es EXCLUSIVO del
superusuario (lo corta `middleware.AdminSoloSuperusuario`); los
administradores (is_staff) trabajan en /panel/, que tiene sus propias
vistas y plantillas. Este archivo sigue siendo la puerta a todas las
tablas —organismos, municipios, grupos, perfiles— para el superusuario.

Además del registro a secas, este archivo define tres cosas:

1) **La cara del panel.** `site_header` / `site_title` / `index_title` son la
   marca que se ve en la barra superior y en la pestaña. Lo visual (tarjetas de
   resumen, píldoras de color, botones) vive en `templates/admin/index.html`,
   `templates/admin/panel_resumen.html` y `static/css/admin.css`.

2) **`BaseAdmin`**: la base de todos los modelos del negocio. Unifica
   columnas, filtros, buscador, 25 filas por página y las celdas vacías en «—».

3) **El candado** (ESP-02 / RF-13: «los usuarios solo pueden acceder a las
   funciones permitidas según su rol»):

   ┌────────────────────┬─────────────────────┬──────────────────────┐
   │ Módulo             │ Editor (is_staff)   │ Superusuario         │
   ├────────────────────┼─────────────────────┼──────────────────────┤
   │ Trámites, Requisi- │ lo gestiona desde   │ alta, edición,       │
   │ tos, Enlaces,      │ /panel/ (no pasa   │ borrado y TODO el    │
   │ Temas, Consultas   │ por /admin/)        │ /admin/              │
   │ Municipios,        │ no llega (middleware│ sí                   │
   │ Organismos,        │ lo manda a /panel/) │                      │
   │ Usuarios, Grupos,  │ —                   │ sí                   │
   │ Perfiles           │                     │                      │
   └────────────────────┴─────────────────────┴──────────────────────┘

   Reglas de cuenta: nadie edita ni borra su propia fila (para no quedar
   afuera del sistema ni auto-bajarse), el borrado de cualquier modelo del
   negocio es exclusivo del superusuario (`BaseAdmin.has_delete_permission`)
   y solo puede existir UN superusuario (la regla la corta `senales.py`;
   `UserAdmin.save_model` evita el 500 si alguien lo intenta desde acá).
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    ArchivoTramite, Consulta, Direccion, Enlace, Municipio, Organismo,
    Perfil, Requisito, Tema, Tramite,
)

# --- La marca del panel -------------------------------------------------------
admin.site.site_header = 'Munitramites · Panel de administración'
admin.site.site_title = 'Munitramites'
admin.site.index_title = 'Resumen general'

VACIO = '—'


def pildora(texto, color='gris'):
    """Etiqueta de color para las columnas (colores en static/css/admin.css)."""
    return format_html('<span class="pildora pildora--{}">{}</span>', color, texto)


# --- Módulos sensibles: solo el superusuario ---------------------------------
class SoloSuperusuario(admin.ModelAdmin):
    """Módulo reservado al superusuario.

    Cuentas, grupos (= los roles del documento) y perfiles (rol) son datos
    sensibles: no se listan, no se abren por URL directa y no se crean. Para
    cualquier otro rol todo devuelve False y Django contesta 403.
    """

    empty_value_display = VACIO
    list_per_page = 25

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class SinAutogestion:
    """Nadie se edita ni se borra a sí mismo desde el listado de usuarios.

    Si un administrador se toca la propia fila se puede quedar sin cuenta
    (o sin `is_staff`) y quedar afuera del sistema. La fila propia se muestra
    en modo lectura y el guardado responde 403.
    """

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.pk == request.user.pk:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.pk == request.user.pk:
            return False
        return super().has_delete_permission(request, obj)


# --- Base de los modelos del negocio ----------------------------------------
class BaseAdmin(admin.ModelAdmin):
    """Base de Trámites, Consultas, Municipios, Organismos, Requisitos,
    Enlaces y Direcciones.

    Amigable: columnas con significado, filtros, buscador y «—» en las celdas
    vacías. Cerrado: el borrado queda para el superusuario; quien es solo
    `is_staff` puede crear y editar, pero no dar de baja nada del sistema.

    Aclaración: sacar un requisito o un enlace de la ficha de un trámite sí
    se puede (es editar el trámite, con los inlines del formulario); lo que
    queda reservado es el borrado desde el listado del modelo.
    """

    empty_value_display = VACIO
    list_per_page = 25

    def has_delete_permission(self, request, obj=None):
        return (
            request.user.is_superuser
            and super().has_delete_permission(request, obj)
        )


# --- Municipios ---------------------------------------------------------------
@admin.register(Municipio)
class MunicipioAdmin(BaseAdmin):
    """Municipios en los que se agrupan los trámites."""

    list_display = ['id', 'nombre', 'tramites']
    search_fields = ['nombre']
    ordering = ['nombre']

    def get_queryset(self, request):
        # Un COUNT por municipio: la columna «Trámites» no hace N+1.
        return super().get_queryset(request).annotate(cantidad_tramites=Count('tramites'))

    @admin.display(description='Trámites', ordering='cantidad_tramites')
    def tramites(self, obj):
        return obj.cantidad_tramites


# --- Organismos (RF-05) -------------------------------------------------------
@admin.register(Organismo)
class OrganismoAdmin(BaseAdmin):
    """Organismo responsable y su área de ocupación (columna «ocupacion»)."""

    list_display = ['id', 'nombre', 'ocupacion', 'direccion', 'tramites']
    list_filter = ['ocupacion']
    search_fields = ['nombre', 'direccion', 'ocupacion']
    ordering = ['nombre']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(cantidad_tramites=Count('tramites'))

    @admin.display(description='Trámites', ordering='cantidad_tramites')
    def tramites(self, obj):
        return obj.cantidad_tramites


# --- Requisitos y enlaces oficiales (se cargan desde la ficha del trámite) -----
class RequisitoInline(admin.TabularInline):
    model = Requisito
    extra = 1
    ordering = ['orden']


class EnlaceInline(admin.TabularInline):
    """Botones que se ven en la ficha del tramite.

    El admin escribe el nombre del boton y la URL: es lo que se muestra
    en «Enlaces oficiales» de la vista de tramite.
    """

    model = Enlace
    extra = 1
    ordering = ['orden']
    fields = ['orden', 'nombre', 'url']


class DireccionInline(admin.TabularInline):
    """Sedes de atención del trámite: varias por trámite y por municipio."""

    model = Direccion
    extra = 1
    fields = ['lugar', 'municipio', 'direccion']
    autocomplete_fields = ['municipio']
    ordering = ['municipio__nombre', 'lugar']


class ArchivoInline(admin.TabularInline):
    """Documentos y formularios descargables de la ficha."""

    model = ArchivoTramite
    extra = 1
    fields = ['orden', 'titulo', 'tipo', 'archivo', 'descripcion']
    ordering = ['orden']


@admin.register(ArchivoTramite)
class ArchivoTramiteAdmin(BaseAdmin):
    """Archivos subidos desde el panel: formularios, instructivos y más."""

    list_display = ['id', 'tramite', 'titulo', 'tipo', 'orden']
    list_filter = ['tipo']
    search_fields = ['titulo', 'descripcion', 'tramite__titulo']
    list_select_related = ['tramite']
    autocomplete_fields = ['tramite']
    ordering = ['tramite', 'orden']


@admin.register(Direccion)
class DireccionAdmin(BaseAdmin):
    """Direcciones de atención, con su municipio y su trámite."""

    list_display = ['id', 'tramite', 'lugar', 'municipio', 'direccion']
    list_filter = ['municipio']
    search_fields = [
        'lugar', 'direccion', 'tramite__titulo', 'municipio__nombre',
    ]
    list_select_related = ['tramite', 'municipio']
    autocomplete_fields = ['tramite', 'municipio']
    ordering = ['tramite', 'municipio__nombre', 'lugar']


@admin.register(Enlace)
class EnlaceAdmin(BaseAdmin):
    list_display = ['id', 'tramite', 'nombre', 'url', 'orden']
    list_filter = ['tramite']
    search_fields = ['nombre', 'url', 'tramite__titulo']
    autocomplete_fields = ['tramite']
    ordering = ['tramite', 'orden']


@admin.register(Requisito)
class RequisitoAdmin(BaseAdmin):
    list_display = ['id', 'tramite', 'orden', 'descripcion']
    list_filter = ['tramite']
    search_fields = ['descripcion', 'tramite__titulo']
    ordering = ['tramite', 'orden']


# --- Temas (tabla nueva: se cargan desde el panel) ------------------------------------------------
@admin.register(Tema)
class TemaAdmin(BaseAdmin):
    """Tema de los trámites: antes un combo fijo, ahora filas que carga
    el administrador; cualquier fila nueva ya aparece en el formulario."""

    list_display = ['id', 'nombre', 'tramites']
    search_fields = ['nombre']
    ordering = ['nombre']

    def get_queryset(self, request):
        # Un COUNT por tema: la columna «Trámites» no hace N+1.
        return super().get_queryset(request).annotate(
            cantidad_tramites=Count('tramites')
        )

    @admin.display(description='Trámites', ordering='cantidad_tramites')
    def tramites(self, obj):
        return obj.cantidad_tramites


# --- Trámites (RF-07) ---------------------------------------------------------
@admin.register(Tramite)
class TramiteAdmin(BaseAdmin):
    """El catálogo público: alta, edición, filtros y publicación masiva."""

    def get_queryset(self, request):
        # La búsqueda por direcciones puede repetir filas: se deduplica.
        return super().get_queryset(request).distinct()

    list_display = [
        'id', 'titulo', 'tema_pildora', 'modalidad_pildora',
        'municipio', 'organismo', 'destacado', 'activo',
    ]
    list_filter = ['tema', 'modalidad', 'municipio', 'organismo', 'destacado', 'activo']
    search_fields = [
        'titulo', 'descripcion', 'organismo__nombre', 'municipio__nombre',
        'direcciones__lugar', 'direcciones__direccion',
        'direcciones__municipio__nombre',
    ]
    list_select_related = ['tema', 'municipio', 'organismo']
    list_editable = ['destacado', 'activo']
    ordering = ['-destacado', 'titulo']
    autocomplete_fields = ['municipio', 'organismo']
    radio_fields = {'modalidad': admin.HORIZONTAL}
    # Acciones masivas: publicar / dar de baja sin entrar a cada ficha.
    # Ojo: el borrado real (delete_selected) solo lo ve el superusuario.
    actions = ['activar', 'desactivar']
    inlines = [EnlaceInline, RequisitoInline, DireccionInline, ArchivoInline]
    fieldsets = (
        ('Datos principales', {
            'fields': ('titulo', 'tema', 'modalidad', 'descripcion'),
        }),
        ('Organización', {
            'fields': ('municipio', 'organismo', 'destacado', 'activo'),
        }),
        ('Enlaces antiguos (solo se usan si el tramite no tiene botones arriba)', {
            'fields': ('enlace_turnos', 'enlace_oficial'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Tema', ordering='tema__nombre')
    def tema_pildora(self, obj):
        colores = {
            'Documentación': 'azul', 'Tránsito': 'gris', 'Comercio': 'morado',
            'Seguridad': 'rojo', 'Salud': 'verde', 'Impuestos': 'ambar',
            'Vivienda': 'gris',
        }
        return pildora(str(obj.tema), colores.get(str(obj.tema), 'gris'))

    @admin.display(description='Modalidad', ordering='modalidad')
    def modalidad_pildora(self, obj):
        colores = {'presencial': 'azul', 'virtual': 'verde', 'mixta': 'morado'}
        return pildora(obj.get_modalidad_display(), colores.get(obj.modalidad, 'gris'))

    @admin.action(description='Activar los trámites seleccionados')
    def activar(self, request, queryset):
        cantidad = queryset.update(activo=True)
        self.message_user(request, f'{cantidad} trámite(s) publicados.',
                          messages.SUCCESS)

    @admin.action(description='Desactivar los trámites seleccionados')
    def desactivar(self, request, queryset):
        cantidad = queryset.update(activo=False)
        self.message_user(request, f'{cantidad} trámite(s) desactivados.',
                          messages.SUCCESS)


# --- Consultas de los ciudadanos ---------------------------------------------
@admin.register(Consulta)
class ConsultaAdmin(BaseAdmin):
    """Consultas, sugerencias y reclamos que llegan desde los formularios."""

    list_display = [
        'id', 'tipo_pildora', 'asunto', 'estado_pildora',
        'usuario', 'tramite', 'fecha',
    ]
    list_filter = ['tipo', 'estado', 'fecha']
    search_fields = ['asunto', 'contenido', 'respuesta', 'usuario__username']
    list_select_related = ['usuario', 'tramite']
    ordering = ['-fecha']
    autocomplete_fields = ['tramite']
    radio_fields = {'tipo': admin.HORIZONTAL, 'estado': admin.VERTICAL}
    actions = ['responder', 'cerrar']
    fieldsets = (
        ('Consulta', {
            'fields': ('tipo', 'asunto', 'contenido', 'tramite', 'usuario', 'fecha'),
        }),
        ('Respuesta', {
            'fields': ('estado', 'respuesta'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """`usuario` (quién la mandó) y `fecha` son registro: no se editan.

        `usuario` solo se vuelve de solo lectura cuando ya está cargado; así,
        si un admin crea una consulta a mano, puede decir de quién es.
        """
        campos = ['fecha']
        if obj is not None and obj.usuario_id:
            campos.insert(0, 'usuario')
        return campos

    def save_model(self, request, obj, form, change):
        # Si se responde por primera vez, pasa a "respondido"
        if obj.respuesta and obj.estado == Consulta.Estado.PENDIENTE:
            obj.estado = Consulta.Estado.RESPONDIDO
        super().save_model(request, obj, form, change)

    @admin.action(description='Marcar como respondidas (las que ya tienen respuesta)')
    def responder(self, request, queryset):
        total = queryset.count()
        con_respuesta = queryset.exclude(respuesta='').update(
            estado=Consulta.Estado.RESPONDIDO
        )
        sin = total - con_respuesta
        if sin:
            self.message_user(
                request,
                f'{con_respuesta} consulta(s) pasaron a «Respondido». '
                f'{sin} quedaron igual: todavía no tienen respuesta cargada.',
                messages.WARNING,
            )
        else:
            self.message_user(request, f'{con_respuesta} consulta(s) respondidas.',
                              messages.SUCCESS)

    @admin.action(description='Cerrar las consultas seleccionadas')
    def cerrar(self, request, queryset):
        cantidad = queryset.update(estado=Consulta.Estado.CERRADO)
        self.message_user(request, f'{cantidad} consulta(s) cerradas.',
                          messages.SUCCESS)

    @admin.display(description='Tipo', ordering='tipo')
    def tipo_pildora(self, obj):
        colores = {'consulta': 'azul', 'sugerencia': 'morado', 'reclamo': 'rojo'}
        return pildora(obj.get_tipo_display(), colores.get(obj.tipo, 'gris'))

    @admin.display(description='Estado', ordering='estado')
    def estado_pildora(self, obj):
        colores = {'pendiente': 'ambar', 'respondido': 'verde', 'cerrado': 'gris'}
        return pildora(obj.get_estado_display(), colores.get(obj.estado, 'gris'))


# --- Perfiles (rol) -----------------------------------------------------------
@admin.register(Perfil)
class PerfilAdmin(SoloSuperusuario):
    """El rol de cada cuenta, identificado por su id: solo superusuario."""

    list_display = ['id', 'user', 'etiqueta_rol', 'actualizado']
    search_fields = ['user__username', 'user__email']
    list_select_related = ['user']
    ordering = ['user']

    @admin.display(description='Rol', ordering='rol')
    def etiqueta_rol(self, obj):
        return obj.get_rol_display()


# --- Usuarios y grupos (RF-11 / ESP-02) ---------------------------------------
class PerfilInline(admin.StackedInline):
    """El rol de la cuenta, de solo lectura (se cambia desde /panel/)."""

    model = Perfil
    extra = 0
    max_num = 0
    readonly_fields = ['rol']
    can_delete = False


class UserAdmin(SinAutogestion, SoloSuperusuario, BaseUserAdmin):
    """Cuentas: solo superusuario, y nunca la fila de uno mismo.

    Para cambiar la contraseña propia se usa «Cambiar mi contraseña» del
    panel, que es el flujo de Django (y no se puede tocar desde la lista).

    `save_model` además atrapa la regla de `senales.py` (un solo
    superusuario): si alguien intenta elevar una cuenta o crear un segundo
    superusuario desde acá, el formulario avisa con un mensaje en lugar de
    tirar un 500.
    """

    inlines = [PerfilInline]
    list_display = ['username', 'email', 'rol', 'is_active', 'last_login']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['username', 'email']
    list_select_related = True
    ordering = ['username']

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))

    @admin.display(description='Rol', ordering='is_superuser')
    def rol(self, obj):
        if obj.is_superuser:
            return pildora('Superusuario', 'morado')
        perfil = getattr(obj, 'perfil', None)
        colores = {
            Perfil.Rol.ADMINISTRADOR: 'azul',
            Perfil.Rol.ADMINISTRATIVO: 'ambar',
            Perfil.Rol.CORRIENTE: 'gris',
        }
        if perfil is not None:
            return pildora(perfil.get_rol_display(), colores.get(perfil.rol))
        # Cuenta vieja sin perfil: is_staff es el espejo del rol
        return pildora(
            'Administrativo' if obj.is_staff else 'Corriente',
            'ambar' if obj.is_staff else 'gris',
        )


# Django ya registró User y Group con sus admins por defecto: hay que
# reemplazarlos (User, para sumar el perfil; Group, para acotarlo).
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.unregister(Group)


@admin.register(Group)
class GrupoAdmin(SoloSuperusuario):
    """Los roles del documento, como grupos de Django: solo superusuario."""

    list_display = ['id', 'name']
    search_fields = ['name']
    ordering = ['name']
    filter_horizontal = ['permissions']
