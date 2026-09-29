"""Soporte del sitio (solo con cuenta logueada).

Lo que llega se guarda como una Consulta con el asunto empezando por
«Soporte: », asi aparece en el admin y en «Mis consultas» y se responde con
el mismo flujo que una consulta normal, sin una tabla nueva.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import SoporteForm
from ..models import Consulta

# Prefijo que identifica los pedidos de soporte dentro de las consultas.
PREFIJO_SOPORTE = 'Soporte: '


@login_required
def soporte(request):
    """Pagina de soporte: formulario + historial de pedidos del usuario."""
    if request.method == 'POST':
        form = SoporteForm(request.POST)
        if form.is_valid():
            Consulta.objects.create(
                tipo=Consulta.Tipo.CONSULTA,
                asunto=f"{PREFIJO_SOPORTE}{form.cleaned_data['asunto']}",
                contenido=form.cleaned_data['mensaje'],
                usuario=request.user,
            )
            messages.success(
                request,
                'Pedido enviado al soporte. Te respondemos en «Mis consultas».'
            )
            return redirect('soporte')
    else:
        form = SoporteForm()

    mis_pedidos = Consulta.objects.filter(
        usuario=request.user,
        asunto__startswith=PREFIJO_SOPORTE,
    )

    return render(request, 'soporte.html', {
        'form': form,
        'mis_pedidos': mis_pedidos[:10],
    })
