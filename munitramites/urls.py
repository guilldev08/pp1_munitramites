"""
URLs del proyecto. >>> ACÁ SE AGREGAN LAS URLS <<<

Orden importa. Django recorre la lista de arriba hacia abajo y se queda con
la primera que coincida:

  1. Admin nativo de Django (usuarios, permisos, modelos)
  2. Autenticacion (login, logout, cambio de clave)
  3. Estaticos del frontend (assets, locales, favicon)
  4. Panel /admin protegido con sesion
  5. Catch-all de la SPA, SIEMPRE al final

Si metes una URL nueva abajo del catch-all, la SPA se la traga y nunca va a
llegar. Arriba del catch-all, pero abajo del login, o vas a romper el login.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.views.static import serve

from . import views


class LogoutView(auth_views.LogoutView):
    """Django 5 exige POST para cerrar sesion; aqui aceptamos GET tambien
    para poder cerrar sesion con un link simple desde la SPA."""
    http_method_names = ['get', 'post', 'options']


urlpatterns = [
    # 1. Admin nativo de Django -------------------------------------------
    # Cambia 'django-admin/' por la ruta que quieras (ej. 'panel/').
    path('django-admin/', admin.site.urls),

    # 2. Autenticacion con los usuarios de Django -------------------------
    path(
        'admin/login/',
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name='login',
    ),
    path('admin/logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path(
        'admin/password/change/',
        auth_views.PasswordChangeView.as_view(
            success_url='/admin/password/change/done/',
        ),
        name='password_change',
    ),
    path(
        'admin/password/change/done/',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),

    # 3. Estaticos del frontend -------------------------------------------
    re_path(
        r'^assets/(?P<path>.*)$',
        serve,
        {'document_root': settings.FRONTEND_DIR / 'assets'},
        name='frontend-assets',
    ),
    re_path(
        r'^locales/(?P<path>.*)$',
        serve,
        {'document_root': settings.FRONTEND_DIR / 'locales'},
        name='frontend-locales',
    ),
    re_path(
        r'^favicon\.ico$',
        serve,
        {'document_root': settings.FRONTEND_DIR, 'path': 'favicon.ico'},
        name='favicon',
    ),

    # 4. Panel del SPA, protegido con sesion ------------------------------
    # 'admin' sin barra tambien: si no, /admin se colaria por el catch-all
    # y el panel se veria sin haber iniciado sesion.
    path('admin', views.spa_admin, name='spa-admin-raw'),
    path('admin/', views.spa_admin, name='spa-admin'),
    path('admin/<path:subpath>', views.spa_admin, name='spa-admin-sub'),

    # 5. SPA publica (catch-all) >>> NUNCA AGREGUES COSAS DEBAJO <<<<<<<<<
    path('', views.spa, name='spa'),
    path('<path:subpath>', views.spa, name='spa-sub'),
]
