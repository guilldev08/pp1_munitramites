"""
Registro de modelos en /admin/. >>> ACÁ SE HACEN VISIBLES <<<

Solo aparece en el admin lo que registres aqui. Con esto solo ya tenes
CRUD completo: alta, baja, edicion, busqueda, filtros y exportacion.
"""

from django.contrib import admin

from .models import Consulta, Enlace, Municipio, Organismo, Requisito, Tramite


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']


@admin.register(Organismo)
class OrganismoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'direccion']
    search_fields = ['nombre', 'direccion']


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


@admin.register(Enlace)
class EnlaceAdmin(admin.ModelAdmin):
    list_display = ['id', 'tramite', 'nombre', 'url', 'orden']
    list_filter = ['tramite']
    search_fields = ['nombre', 'url']
    autocomplete_fields = ['tramite']


@admin.register(Tramite)
class TramiteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'titulo', 'tema', 'modalidad',
        'municipio', 'organismo', 'destacado', 'activo',
    ]
    list_filter = ['tema', 'modalidad', 'municipio', 'organismo', 'destacado', 'activo']
    search_fields = ['titulo', 'descripcion']
    list_editable = ['destacado', 'activo']
    autocomplete_fields = ['municipio', 'organismo']
    inlines = [EnlaceInline, RequisitoInline]
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


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'asunto', 'estado', 'usuario', 'tramite', 'fecha']
    list_filter = ['tipo', 'estado', 'fecha']
    search_fields = ['asunto', 'contenido', 'respuesta']
    readonly_fields = ['fecha']
    autocomplete_fields = ['tramite']
    fieldsets = (
        ('Consulta', {
            'fields': ('tipo', 'asunto', 'contenido', 'tramite', 'usuario', 'fecha'),
        }),
        ('Respuesta', {
            'fields': ('estado', 'respuesta'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Si se responde por primera vez, pasa a "respondido"
        if obj.respuesta and obj.estado == Consulta.Estado.PENDIENTE:
            obj.estado = Consulta.Estado.RESPONDIDO
        super().save_model(request, obj, form, change)


@admin.register(Requisito)
class RequisitoAdmin(admin.ModelAdmin):
    list_display = ['id', 'tramite', 'orden', 'descripcion']
    list_filter = ['tramite']
    search_fields = ['descripcion']
