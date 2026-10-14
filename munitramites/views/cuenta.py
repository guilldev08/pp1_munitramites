"""Cuenta del ciudadano: registro y perfil.

RF-01 (registro): el sitio pide lo mínimo —usuario, correo y
contraseña—, sin documentos ni nombres. El perfil de cada cuenta solo
carga el rol (ver `models.Perfil`).

La clave olvidada (RF-15) no tiene vista propia: la resuelven las vistas
de Django montadas en `urls.py`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import PerfilForm, RegistroForm
from ..models import Perfil


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

    # form_registro es lo que pinta la pestaña «Crear cuenta» del modal:
    # si el POST vino con errores, manda el form validoado para que se vea.
    return render(request, 'registro.html', {
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
