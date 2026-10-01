"""
URLs del proyecto. >>> ACÁ SE AGREGAN LAS URLS <<<

Este archivo junta las rutas de todo el sitio. La logica de cada ruta vive
en `views/` (una carpeta por modulo: pagina, tramites, chatbot, …).

Orden importa. Django recorre la lista de arriba hacia abajo y se queda con
la primera que coincida:

  1. Admin nativo de Django (/admin) — CRUD completo de todas las tablas
  2. Autenticacion de ciudadanos (login, clave olvidada, registro, perfil)
  3. Paginas del sitio (portada, tramites, chatbot, consultas, soporte)
  4. API liviana
  5. Estaticos en desarrollo

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
    # CRUD de Municipio, Organismo, Tramite, Requisito, Consulta, Enlace,
    # Perfil y usuarios. Login propio en /admin/login/.
    path('admin/', admin.site.urls),

    # 2. Autenticacion de ciudadanos --------------------------------------
    path(
        'login/',
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name='login',
    ),
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
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chatbot/api/', views.chatbot_api, name='chatbot_api'),
    path('buscador/api/', views.buscador_api, name='buscador_api'),
    path('chatbot/limpiar/', views.chatbot_limpiar, name='chatbot_limpiar'),
    path('soporte/', views.soporte, name='soporte'),
    path('consultas/', views.consultas, name='consultas'),
    path('consultas/nueva/', views.consulta_nueva, name='consulta_nueva'),
    path('consultas/<int:pk>/', views.consulta_detalle, name='consulta_detalle'),

    # 4. API ----------------------------------------------------------------
    path('api/tramites/', views.api_tramites, name='api_tramites'),
]

# Estaticos en desarrollo. En produccion los sirve el servidor web
# (gunicorn + whitenoise o nginx), nunca Django.
if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.BASE_DIR / 'static'
    )
