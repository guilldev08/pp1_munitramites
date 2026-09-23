"""
URL configuration for munitramites project.

Orden importante: primero las rutas especificas de Django (auth, admin nativo,
estaticos) y al final el catch-all de la SPA, si no la SPA se traga todo.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.views.static import serve

from . import views


class LogoutView(auth_views.LogoutView):
    """Django 5 exige POST para cerrar sesion; aqui tambien aceptamos GET
    para poder cerrar sesion con un link simple desde la SPA."""
    http_method_names = ['get', 'post', 'options']


urlpatterns = [
    # --- Autenticacion con los usuarios de Django -------------------------
    path(
        'admin/login/',
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name='login',
    ),
    path('admin/logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path(
        'admin/password/change/',
        auth_views.PasswordChangeView.as_view(success_url='/admin/password/change/done/'),
        name='password_change',
    ),
    path(
        'admin/password/change/done/',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),

    # --- Admin nativo de Django (gestion de usuarios y modelos) -----------
    path('django-admin/', admin.site.urls),

    # --- Panel del SPA, protegido con login de Django ---------------------
    # Debe ir despues de admin/login/ y admin/logout/ para no taparlos.
    # 'admin' sin barra tambien: si no, APPEND_SLASH no redirige (porque
    # /admin si resuelve en el catch-all) y el panel se veria sin sesion.
    path('admin', views.spa_admin, name='spa-admin-raw'),
    path('admin/', views.spa_admin, name='spa-admin'),
    path('admin/<path:subpath>', views.spa_admin, name='spa-admin-sub'),

    # --- Estaticos del frontend ------------------------------------------
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

    # --- SPA publica (catch-all) -----------------------------------------
    path('', views.spa, name='spa'),
    path('<path:subpath>', views.spa, name='spa-sub'),
]
