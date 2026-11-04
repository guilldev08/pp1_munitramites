"""Consultas y sugerencias de los ciudadanos (RF-08, RF-09, RF-10).

El ciudadano ve las suyas. El administrador (is_staff) ve todas y responde
desde /admin/ (o desde aca, con el mismo formulario).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

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
    """Alta de consulta. Solo POST a la base si el form valida.

    El staff no envía consultas: su canal es responder las que llegan
    (Centro de Consultas del panel) y, si necesita registrar algo, los
    tickets internos del dashboard.
    """
    if request.user.is_staff and not request.user.is_superuser:
        messages.info(
            request,
            'Las consultas las envían los ciudadanos. Como gestor, '
            'respondelas desde el panel.'
        )
        return redirect('panel')

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
            if not consulta.fecha_respuesta:
                consulta.fecha_respuesta = timezone.now()
                consulta.respondido_por = request.user
            consulta.save(update_fields=[
                'respuesta', 'estado', 'fecha_respuesta', 'respondido_por',
            ])
            messages.success(request, 'Respuesta enviada al ciudadano.')
        return redirect('consulta_detalle', pk=consulta.pk)

    return render(request, 'consultas/detalle.html', {
        'consulta': consulta,
        'puede_responder': request.user.is_staff,
    })


@login_required
def consulta_editar(request, pk):
    """Edición de una consulta: solo el dueño o el superusuario.

    El staff (administrativo/administrador) ya no puede editar el texto
    de una consulta ajena: solo la responde desde el panel. Al guardar
    se registra la hora de la última edición.
    """
    consulta = get_object_or_404(Consulta, pk=pk)
    es_duenio = consulta.usuario_id == request.user.pk
    if not (es_duenio or request.user.is_superuser):
        messages.error(request, 'No podés editar la consulta de otra persona.')
        if request.user.is_staff:
            return redirect('panel_consulta', pk=consulta.pk)
        return redirect('consultas')

    # Si se editó desde el panel, se vuelve al panel en vez de a la vista
    # del ciudadano.
    origen = request.POST.get('origen') or request.GET.get('origen') or ''

    if request.method == 'POST':
        form = ConsultaForm(request.POST, instance=consulta)
        if form.is_valid():
            consulta = form.save(commit=False)
            consulta.fecha_edicion = timezone.now()
            consulta.save()
            messages.success(request, 'Consulta actualizada.')
            if origen == 'panel' and request.user.is_staff:
                return redirect('panel_consulta', pk=consulta.pk)
            return redirect('consulta_detalle', pk=consulta.pk)
    else:
        form = ConsultaForm(instance=consulta)

    return render(request, 'consultas/editar.html', {
        'form': form,
        'consulta': consulta,
        'origen': origen,
    })


@login_required
@require_POST
def consulta_eliminar(request, pk):
    """Borra una consulta: solo el dueño o el superusuario; siempre por POST.

    GET no borra nada: así un enlace o un redirect no elimina datos por
    accidente. Si la consulta no es del usuario, se trata como inexistente.
    """
    consulta = get_object_or_404(Consulta, pk=pk)
    es_duenio = consulta.usuario_id == request.user.pk
    if not (es_duenio or request.user.is_superuser):
        messages.error(request, 'No podés borrar la consulta de otra persona.')
        if request.user.is_staff:
            return redirect('panel_consulta', pk=consulta.pk)
        return redirect('consultas')

    numero = consulta.pk
    consulta.delete()
    messages.success(request, f'Consulta #{numero} eliminada.')

    # El panel vuelve al Centro de Consultas; el ciudadano, a «Mis consultas».
    if request.POST.get('origen') == 'panel' and request.user.is_staff:
        return redirect('panel_consultas')
    return redirect('consultas')
