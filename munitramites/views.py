"""
Vistas que sirven el frontend (SPA construida con Vite/React).

El frontend es 100% estatico: sus datos van hardcodeados en el bundle, no
llama a ninguna API. Django unicamente se encarga de entregar el HTML y de
proteger el panel /admin con los usuarios de Django.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers

FRONTEND_DIR = Path(settings.FRONTEND_DIR)


def _index_response():
    """Devuelve el index.html de la SPA (el React Router maneja las rutas)."""
    index = FRONTEND_DIR / 'index.html'
    if not index.exists():
        raise Http404('No se encontro frontend/index.html')
    return FileResponse(open(index, 'rb'), content_type='text/html')


@vary_on_headers('Cookie')
@cache_control(no_store=True)
def spa(request, subpath=None):
    """Cualquier ruta publica: /, /tramites, /tramites/3, /chatbot, /login..."""
    return _index_response()


@login_required
@vary_on_headers('Cookie')
@cache_control(no_store=True)
def spa_admin(request, subpath=None):
    """Panel del SPA (/admin, /admin/tramites, ...).

    Exige iniciar sesion con un usuario de Django. Si no hay sesion,
    login_required redirige a /admin/login/?next=...
    """
    return _index_response()
