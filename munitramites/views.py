"""
Vistas de la SPA.

Django solo entrega el index.html; React Router resuelve las rutas en el
cliente. El frontend es 100% estatico: sus datos van hardcodeados en el
bundle y no llama a ninguna API.

Si necesitas una vista que SI haga algo (leer/escribir en Firebird), creala
aqui y sumala en munitramites/urls.py ANTES del catch-all del final.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers

FRONTEND_DIR = Path(settings.FRONTEND_DIR)


def _index_response():
    """Devuelve frontend/index.html."""
    index = FRONTEND_DIR / 'index.html'
    if not index.exists():
        raise Http404('No se encontro frontend/index.html')
    return FileResponse(open(index, 'rb'), content_type='text/html')


@vary_on_headers('Cookie')
@cache_control(no_store=True)
def spa(request, subpath=None):
    """Rutas publicas: /, /tramites, /tramites/3, /chatbot, /login..."""
    return _index_response()


@login_required
@vary_on_headers('Cookie')
@cache_control(no_store=True)
def spa_admin(request, subpath=None):
    """Panel del SPA (/admin, /admin/tramites, /admin/usuarios...).

    Exige sesion de Django. login_required redirige a /admin/login/?next=...
    """
    return _index_response()
