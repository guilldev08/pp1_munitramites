"""
URLs del proyecto. >>> ACÁ SE AGREGAN LAS URLS <<<

Orden importa. Django recorre la lista de arriba hacia abajo y se queda con
la primera que coincida:

  1. Admin nativo de Django (/admin) — CRUD completo de todas las tablas
  2. Autenticacion de ciudadanos (login, logout, clave, registro)
  3. Paginas del sitio (portada, tramites, chatbot, consultas)
  4. API liviana
  5. Estáticos en desarrollo

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
    # CRUD de Municipio, Organismo, Tramite, Requisito, Consulta y usuarios.
    # Login propio en /admin/login/.
    path('admin/', admin.site.urls),

    # 2. Autenticacion de ciudadanos --------------------------------------
    path(
        'login/',
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(success_url='/password/change/done/'),
        name='password_change',
    ),
    path(
        'password/change/done/',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),
    path('registro/', views.registro, name='registro'),

    # 3. Paginas del sitio --------------------------------------------------
    path('', views.inicio, name='inicio'),
    path('tramites/', views.tramites, name='tramites'),
    path('tramites/<int:pk>/', views.tramite_detalle, name='tramite_detalle'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chatbot/api/', views.chatbot_api, name='chatbot_api'),
    path('chatbot/limpiar/', views.chatbot_limpiar, name='chatbot_limpiar'),
    path('soporte/', views.soporte, name='soporte'),
    path('consultas/', views.consultas, name='consultas'),
    path('consultas/nueva/', views.consulta_nueva, name='consulta_nueva'),

    # 4. API ----------------------------------------------------------------
    path('api/tramites/', views.api_tramites, name='api_tramites'),
]

# Estáticos en desarrollo. En producción los sirve el servidor web
# (gunicorn + whitenoise o nginx), nunca Django.
if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.BASE_DIR / 'static'
    )
