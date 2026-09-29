"""Consultas y sugerencias de los ciudadanos (RF-08, RF-09, RF-10).

El ciudadano ve las suyas. El administrador (is_staff) ve todas y responde
desde /admin/ (o desde aca, con el mismo formulario).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ConsultaForm
from ..models import Consulta


@login_required
def consultas(request):
    """Listado de consultas. El ciudadano ve las suyas; el staff, todas."""
    if request.user.is_staff:
        consultas_qs = Consulta.objects.select_related('usuario', 'tramite')
    else:
        consultas_qs = Consulta.objects.filter(
            usuario=request.user
        ).select_related('tramite')

    paginador = Paginator(consultas_qs, 10)
    return render(request, 'consultas/lista.html', {
        'pagina': paginador.get_page(request.GET.get('pagina')),
    })


@login_required
def consulta_nueva(request):
    """Alta de consulta. Solo POST a la base si el form valida."""
    if request.method == 'POST':
        form = ConsultaForm(request.POST)
        if form.is_valid():
            consulta = form.save(commit=False)
            consulta.usuario = request.user
            consulta.save()
            messages.success(
                request,
                'Consulta enviada. Vas a ver la respuesta en «Mis consultas».'
            )
            return redirect('consultas')
    else:
        # Viene de una ficha de tramite: preselecciona el combo
        inicial = {}
        if request.GET.get('tramite'):
            inicial['tramite'] = request.GET['tramite']
        form = ConsultaForm(initial=inicial)

    return render(request, 'consultas/nueva.html', {'form': form})


@login_required
def consulta_detalle(request, pk):
    """Detalle de una consulta: para el dueño o para el staff.

    Si el usuario es staff puede responder (RF-10); al responder, la
    consulta pasa a estado «respondido».
    """
    consulta = get_object_or_404(
        Consulta.objects.select_related('usuario', 'tramite'), pk=pk
    )
    es_duenio = consulta.usuario_id == request.user.pk
    if not (es_duenio or request.user.is_staff):
        messages.error(request, 'No tenés acceso a esa consulta.')
        return redirect('consultas')

    if request.method == 'POST' and request.user.is_staff:
        consulta.respuesta = request.POST.get('respuesta', '').strip()
        if consulta.respuesta:
            consulta.estado = Consulta.Estado.RESPONDIDO
            consulta.save(update_fields=['respuesta', 'estado'])
            messages.success(request, 'Respuesta enviada al ciudadano.')
        return redirect('consulta_detalle', pk=consulta.pk)

    return render(request, 'consultas/detalle.html', {
        'consulta': consulta,
        'puede_responder': request.user.is_staff,
    })
