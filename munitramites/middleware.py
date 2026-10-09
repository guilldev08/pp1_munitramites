"""Middleware. >>> ACÁ SE CORTAN PETICIONES ENTERAS <<<

`AdminSoloSuperusuario`: el /admin/ de Django queda reservado al
superusuario. Un administrador (`is_staff`, sin superusuario) que pise
/admin/... no recibe 403 ni un error crudo: recibe un mensaje claro y
termina en el panel propio (/panel/), que es donde trabaja el día a día.

El ciudadano y el anónimo pasan sin cambios: para ellos /admin/ sigue
respondiendo lo de siempre (redirección al login de Django), así los
flujos de autenticación existentes no se tocan.
"""

from django.contrib import messages
from django.shortcuts import redirect


class AdminSoloSuperusuario:
    """Redirige al panel a todo el que no sea superusuario y pise /admin/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path_info
        usuario = getattr(request, 'user', None)
        en_admin = ruta == '/admin' or ruta.startswith('/admin/')

        if (
            en_admin
            and usuario is not None
            and usuario.is_authenticated
            and usuario.is_staff
            and not usuario.is_superuser
        ):
            messages.warning(
                request,
                'El /admin/ de Django es solo para el superusuario: '
                'te llevamos al panel de administración.',
            )
            return redirect('panel')

        return self.get_response(request)
