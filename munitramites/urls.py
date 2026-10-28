"""
URLs del proyecto. >>> ACÁ SE AGREGAN LAS URLS <<<

Este archivo junta las rutas de todo el sitio. La logica de cada ruta vive
en `views/` (una carpeta por modulo: pagina, tramites, chatbot, …).

Orden importa. Django recorre la lista de arriba hacia abajo y se queda con
la primera que coincida:

  1. Admin nativo de Django (/admin) — SOLO superusuario (lo vigila
     munitramites.middleware.AdminSoloSuperusuario; los administradores
     terminan en /panel/)
  2. Autenticacion de ciudadanos (login, clave olvidada, registro, perfil)
  3. Paginas del sitio (portada, tramites, chatbot, consultas, soporte)
  4. Panel propio de administracion (/panel/ — trámites, consultas,
     usuarios y temas; rol Administrador y superusuario)
  5. API liviana
  6. Estaticos en desarrollo

NO hay catch-all: una URL inexistente devuelve el 404 de Django.
Si agregas una ruta nueva, ponla antes de la que empiece con <int:...>.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # 1. Admin nativo de Django -------------------------------------------
    # CRUD de TODAS las tablas (Municipio, Organismo, Tramite, Consulta,
    # usuarios, grupos, perfiles…). EXCLUSIVO del superusuario: un
    # administrador que pise /admin/ queda redirigido a /panel/
    # (ver munitramites/middleware.py). Login propio en /admin/login/.
    path('admin/', admin.site.urls),

    # 2. Autenticacion de ciudadanos --------------------------------------
    # El login no tiene página propia: se pone encima de la landing
    # (base.html abre el modal solo cuando la vista manda `form`).
    # Cerrar el modal deja al visitante en el sitio, no en un vacío.
    path('login/', views.LoginDeSitio.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # RF-15: restablecer la clave olvidada (token por correo)
    path(
        'password/reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            success_url='/password/reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/password/reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # Cambio de clave estando adentro de la sesion
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change_form.html',
            success_url='/password/change/done/',
        ),
        name='password_change',
    ),
    path(
        'password/change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html',
        ),
        name='password_change_done',
    ),

    path('registro/', views.registro, name='registro'),
    path('perfil/', views.perfil, name='perfil'),

    # 3. Paginas del sitio --------------------------------------------------
    path('', views.inicio, name='inicio'),
    path('tramites/', views.tramites, name='tramites'),
    path('tramites/<int:pk>/', views.tramite_detalle, name='tramite_detalle'),
    path('chatbot/api/', views.chatbot_api, name='chatbot_api'),
    path('buscador/api/', views.buscador_api, name='buscador_api'),
    path('soporte/', views.soporte, name='soporte'),
    path('consultas/', views.consultas, name='consultas'),
    path('consultas/nueva/', views.consulta_nueva, name='consulta_nueva'),
    path('consultas/<int:pk>/', views.consulta_detalle, name='consulta_detalle'),

    # 4. Panel propio de administración (rol Administrador y superusuario) --
    # /admin/ de Django queda reservado al superusuario (ver middleware.py):
    # el día a día se maneja acá, con vistas y plantillas propias.
    path('panel/', views.panel, name='panel'),
    path('panel/tramites/', views.panel_tramites, name='panel_tramites'),
    path(
        'panel/tramites/nuevo/', views.panel_tramite_nuevo,
        name='panel_tramite_nuevo',
    ),
    path(
        'panel/tramites/accion/', views.panel_tramites_accion,
        name='panel_tramites_accion',
    ),
    path(
        'panel/tramites/<int:pk>/editar/', views.panel_tramite_editar,
        name='panel_tramite_editar',
    ),
    path(
        'panel/tramites/<int:pk>/estado/', views.panel_tramite_estado,
        name='panel_tramite_estado',
    ),
    path(
        'panel/consultas/', views.panel_consultas, name='panel_consultas'
    ),
    path(
        'panel/consultas/<int:pk>/', views.panel_consulta,
        name='panel_consulta',
    ),
    path('panel/usuarios/', views.panel_usuarios, name='panel_usuarios'),
    path(
        'panel/usuarios/nuevo/', views.panel_usuario_nuevo,
        name='panel_usuario_nuevo',
    ),
    path(
        'panel/usuarios/<int:pk>/editar/', views.panel_usuario_editar,
        name='panel_usuario_editar',
    ),
    path(
        'panel/usuarios/<int:pk>/eliminar/', views.panel_usuario_eliminar,
        name='panel_usuario_eliminar',
    ),
    path('panel/temas/', views.panel_temas, name='panel_temas'),

    # 5. API ----------------------------------------------------------------
    path('api/tramites/', views.api_tramites, name='api_tramites'),
]

# Estaticos en desarrollo. En produccion los sirve el servidor web
# (gunicorn + whitenoise o nginx), nunca Django.
if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.BASE_DIR / 'static'
    )
    # Documentos y formularios subidos desde el panel
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
