"""Cuenta del ciudadano: registro y perfil.

RF-01 (registro): el sitio pide lo mínimo —usuario, correo y
contraseña—, sin documentos ni nombres. El perfil de cada cuenta solo
carga el rol (ver `models.Perfil`).

La clave olvidada (RF-15) no tiene vista propia: la resuelven las vistas
de Django montadas en `urls.py`.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, resolve_url

from ..forms import PerfilForm, RegistroForm
from ..models import Perfil


class LoginDeSitio(auth_views.LoginView):
    """El login del sitio: no tiene página propia.

    Renderiza la landing y base.html abre el modal solo (la vista manda
    `form`), así cerrar el modal deja al visitante en el sitio y no en
    una pantalla en blanco.

    El GET de alguien que ya tiene sesión vuelve al sitio
    (LOGIN_REDIRECT_URL) y no a «next»: redirigirlo a una página a la
    que su rol no entra —por ejemplo /panel/ siendo corriente— cerraba
    en bucle con @login_required. El POST del login sigue respetando
    «next», así quien inicia sesión vuelve a la página que estaba viendo.
    """
    template_name = 'inicio.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.method != 'POST':
            return resolve_url(settings.LOGIN_REDIRECT_URL)
        return super().get_success_url()


def registro(request):
    """Alta de usuario con el sistema de usuarios de Django (RF-01)."""
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'¡Cuenta creada! Ya podés iniciar sesión como {user.username}.'
            )
            return redirect('login')
    else:
        form = RegistroForm()

    # Igual que /login/: no hay página propia. La vista manda `form` con
    # password1/password2 y base.html abre el modal «Crear cuenta» solo,
    # encima de la landing. Si el POST vino con errores, el form validado
    # hace que el modal se vea con ellos.
    return render(request, 'inicio.html', {
        'form': form,
        'form_registro': form,
    })


@login_required
def perfil(request):
    """Ficha de la cuenta: usuario, correo y rol (el correo es editable)."""
    perfil_obj, _ = Perfil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos actualizados.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)

    return render(request, 'cuenta/perfil.html', {
        'form': form,
        'perfil': perfil_obj,
    })
