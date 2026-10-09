"""Panel propio de administración (/panel/). >>> ACÁ SE GESTIONA EL DÍA A DÍA <<<

El sitio tiene dos puertas distintas:

* **`/panel/`** — este módulo. El rol *Administrador* (`is_staff`) y el
  superusuario trabajan acá: Centro de Trámites, Centro de Consultas,
  usuarios y temas. Es el reemplazo amigable del /admin/ de Django.
* **`/admin/`** — Django a pelo, RESERVADO al superusuario (lo vigila
  `middleware.AdminSoloSuperusuario`). Sirve para lo que el panel no hace:
  organismos, municipios, grupos, perfiles y el resto de las tablas.

Reglas de este módulo (ESP-02 / RF-13):

* nadie entra sin sesión (lo manda `@login_required` al login),
* un ciudadano no pasa (mensaje claro y vuelta a la portada),
* el panel NUNCA expone `is_superuser`: no se crean superusuarios desde
  acá ni se edita ni se elimina al superusuario (la regla de la única
  cuenta la corta `senales.py`),
* nadie se edita ni se borra a sí mismo (mismo criterio que el candado
  del /admin/: no quedarse afuera del sistema).
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import (
    EnlaceFormSet, RespuestaConsultaForm, RequisitoFormSet, TemaForm,
    TramitePanelForm, UsuarioPanelForm, UsuarioRolForm,
)
from ..models import Consulta, Tema, Tramite

# Filas por página de los listados del panel
POR_PAGINA = 10


def solo_administrador(vista):
    """Decorador de todas las vistas del panel.

    * Sin sesión → al login (igual que el resto de las páginas privadas).
    * Ciudadano (`is_staff=False`) → mensaje claro + redirect a la portada.
    * Administrador y superusuario → pasan.
    """

    @login_required
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(
                request,
                'Esta sección es solo para administradores del sitio. '
                'Si necesitás acceso, pedile al administrador de la cuenta.',
            )
            return redirect('inicio')
        return vista(request, *args, **kwargs)

    return envuelta


# =============================================================================
# Dashboard (/panel/)
# =============================================================================


@solo_administrador
def panel(request):
    """Resumen general con accesos a los dos centros y a las gestiones."""
    consultas = Consulta.objects
    contexto = {
        'tramites_total': Tramite.objects.count(),
        'tramites_activos': Tramite.objects.filter(activo=True).count(),
        'pendientes': consultas.filter(
            estado=Consulta.Estado.PENDIENTE
        ).count(),
        'consultas_total': consultas.count(),
        'usuarios': User.objects.filter(is_active=True).count(),
        'temas': Tema.objects.count(),
        'es_superusuario': request.user.is_superuser,
    }
    return render(request, 'panel/dashboard.html', contexto)


# =============================================================================
# Centro de Trámites (/panel/tramites/)
# =============================================================================


@solo_administrador
def panel_tramites(request):
    """Listado de trámites (todos: activos e inactivos) con acciones."""
    queryset = Tramite.objects.select_related(
        'tema', 'municipio', 'organismo'
    ).order_by('-activo', '-destacado', 'titulo')

    estado = request.GET.get('estado', '')
    if estado == 'activos':
        queryset = queryset.filter(activo=True)
    elif estado == 'inactivos':
        queryset = queryset.filter(activo=False)

    paginador = Paginator(queryset, POR_PAGINA)
    return render(request, 'panel/tramites_lista.html', {
        'pagina': paginador.get_page(request.GET.get('pagina')),
        'estado': estado,
    })


def _contexto_form_tramite(request, tramite):
    """Form + inlines (requisitos y enlaces) para GET o POST."""
    if request.method == 'POST':
        form = TramitePanelForm(request.POST, instance=tramite)
        requisitos = RequisitoFormSet(request.POST, instance=tramite)
        enlaces = EnlaceFormSet(request.POST, instance=tramite)
    else:
        form = TramitePanelForm(instance=tramite)
        requisitos = RequisitoFormSet(instance=tramite)
        enlaces = EnlaceFormSet(instance=tramite)
    return form, requisitos, enlaces


def _guardar_tramite(request, tramite):
    """Valida form + formsets y guarda todo junto. True si se guardó.

    El trámite se guarda primero (los inlines necesitan su pk) y recién
    después los requisitos y los enlaces, igual que hace el /admin/.
    """
    form, requisitos, enlaces = _contexto_form_tramite(request, tramite)
    if not (form.is_valid() and requisitos.is_valid() and enlaces.is_valid()):
        return False, form, requisitos, enlaces

    tramite = form.save()
    # Los formsets apuntan al MISMO objeto: ya tiene pk al guardarlos.
    requisitos.instance = tramite
    requisitos.save()
    enlaces.instance = tramite
    enlaces.save()
    return True, form, requisitos, enlaces


@solo_administrador
def panel_tramite_nuevo(request):
    """Alta de un trámite con sus requisitos y enlaces oficiales."""
    if request.method == 'POST':
        guardado, form, requisitos, enlaces = _guardar_tramite(
            request, Tramite()
        )
        if guardado:
            messages.success(request, 'Trámite creado y publicado en el sitio.')
            return redirect('panel_tramites')
    else:
        form = TramitePanelForm()
        requisitos = RequisitoFormSet()
        enlaces = EnlaceFormSet()

    return render(request, 'panel/tramite_form.html', {
        'form': form,
        'requisitos': requisitos,
        'enlaces': enlaces,
        'tramite': None,
    })


@solo_administrador
def panel_tramite_editar(request, pk):
    """Edición del trámite: datos, requisitos y enlaces en una sola vista."""
    tramite = get_object_or_404(
        Tramite.objects.select_related('tema', 'municipio', 'organismo'),
        pk=pk,
    )
    if request.method == 'POST':
        guardado, form, requisitos, enlaces = _guardar_tramite(
            request, tramite
        )
        if guardado:
            messages.success(request, 'Trámite guardado.')
            return redirect('panel_tramites')
    else:
        form, requisitos, enlaces = _contexto_form_tramite(request, tramite)

    return render(request, 'panel/tramite_form.html', {
        'form': form,
        'requisitos': requisitos,
        'enlaces': enlaces,
        'tramite': tramite,
    })


@solo_administrador
@require_POST
def panel_tramite_estado(request, pk):
    """Acciones rápidas desde el listado: publicar, desactivar, destacar."""
    tramite = get_object_or_404(Tramite, pk=pk)
    accion = request.POST.get('accion', '')

    if accion == 'activar':
        tramite.activo = True
        mensaje = f'«{tramite.titulo}» ya está publicado.'
    elif accion == 'desactivar':
        tramite.activo = False
        mensaje = f'«{tramite.titulo}» quedó desactivado (no se muestra en el sitio).'
    elif accion == 'destacar':
        tramite.destacado = not tramite.destacado
        if tramite.destacado:
            mensaje = f'«{tramite.titulo}» ahora figura como destacado.'
        else:
            mensaje = f'«{tramite.titulo}» ya no está destacado.'
    else:
        messages.error(request, 'Acción no reconocida.')
        return redirect('panel_tramites')

    tramite.save()
    messages.success(request, mensaje)
    return redirect('panel_tramites')


# =============================================================================
# Centro de Consultas (/panel/consultas/)
# =============================================================================


@solo_administrador
def panel_consultas(request):
    """Todas las consultas de los ciudadanos, con filtro por estado."""
    queryset = Consulta.objects.select_related('usuario', 'tramite')

    estado = request.GET.get('estado', '')
    if estado in dict(Consulta.Estado.choices):
        queryset = queryset.filter(estado=estado)

    paginador = Paginator(queryset, POR_PAGINA)
    return render(request, 'panel/consultas_lista.html', {
        'pagina': paginador.get_page(request.GET.get('pagina')),
        'estado': estado,
    })


@solo_administrador
def panel_consulta(request, pk):
    """Detalle de una consulta y respuesta al ciudadano (RF-10)."""
    consulta = get_object_or_404(
        Consulta.objects.select_related('usuario', 'tramite'), pk=pk
    )

    if request.method == 'POST':
        form = RespuestaConsultaForm(request.POST)
        if form.is_valid():
            consulta.respuesta = form.cleaned_data['respuesta'].strip()
            consulta.estado = Consulta.Estado.RESPONDIDO
            consulta.save(update_fields=['respuesta', 'estado'])
            messages.success(request, 'Respuesta enviada al ciudadano.')
            return redirect('panel_consulta', pk=consulta.pk)
    else:
        form = RespuestaConsultaForm(
            initial={'respuesta': consulta.respuesta}
        )

    return render(request, 'panel/consulta_detalle.html', {
        'consulta': consulta,
        'form': form,
    })


# =============================================================================
# Usuarios (/panel/usuarios/)
# =============================================================================


def _rol(user):
    """Etiqueta del rol para la lista (nunca se tilda el superusuario)."""
    if user.is_superuser:
        return 'superusuario'
    if user.is_staff:
        return 'administrador'
    return 'usuario'


def _cuenta_protegida(request, objetivo):
    """Respuesta de rechazo si la cuenta no se puede tocar desde el panel.

    Devuelve `None` cuando la cuenta se puede editar (todo lo demás: la
    única superusuario y la propia fila quedan afuera, a propósito).
    """
    if objetivo.is_superuser:
        messages.error(
            request,
            'La cuenta de superusuario no se puede editar ni eliminar '
            'desde el panel.',
        )
        return redirect('panel_usuarios')
    if objetivo.pk == request.user.pk:
        messages.error(
            request,
            'No podés editar ni eliminar tu propia cuenta desde el panel: '
            'usá «Mi perfil» y «Cambiar mi contraseña» para lo tuyo.',
        )
        return redirect('panel_usuarios')
    return None


@solo_administrador
def panel_usuarios(request):
    """Listado de cuentas con búsqueda y acciones de rol."""
    queryset = User.objects.all().order_by('username')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        queryset = queryset.filter(
            Q(username__icontains=busqueda)
            | Q(email__icontains=busqueda)
            | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda)
        )

    paginador = Paginator(queryset, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('pagina'))
    return render(request, 'panel/usuarios_lista.html', {
        'pagina': pagina,
        'q': busqueda,
    })


@solo_administrador
def panel_usuario_nuevo(request):
    """Alta de cuentas: usuario común o administrador. Nunca superusuario."""
    if request.method == 'POST':
        form = UsuarioPanelForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.is_staff:
                messages.success(
                    request,
                    f'Cuenta «{user.username}» creada con rol Administrador: '
                    'ya puede entrar al panel.',
                )
            else:
                messages.success(
                    request, f'Cuenta «{user.username}» creada (rol Usuario).'
                )
            return redirect('panel_usuarios')
    else:
        form = UsuarioPanelForm()

    return render(request, 'panel/usuario_form.html', {
        'form': form,
        'editar': False,
        'objetivo': None,
    })


@solo_administrador
def panel_usuario_editar(request, pk):
    """Edición de una cuenta ajena: datos, rol y actividad."""
    objetivo = get_object_or_404(User, pk=pk)
    rechazo = _cuenta_protegida(request, objetivo)
    if rechazo is not None:
        return rechazo

    if request.method == 'POST':
        form = UsuarioRolForm(request.POST, instance=objetivo)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Cuenta «{user.username}» actualizada: rol '
                f'{_rol(user).capitalize()}.',
            )
            return redirect('panel_usuarios')
    else:
        form = UsuarioRolForm(instance=objetivo)

    return render(request, 'panel/usuario_form.html', {
        'form': form,
        'editar': True,
        'objetivo': objetivo,
    })


@solo_administrador
@require_POST
def panel_usuario_eliminar(request, pk):
    """Baja de una cuenta ajena (el perfil y las consultas la siguen)."""
    objetivo = get_object_or_404(User, pk=pk)
    rechazo = _cuenta_protegida(request, objetivo)
    if rechazo is not None:
        return rechazo

    username = objetivo.username
    objetivo.delete()
    messages.success(request, f'Cuenta «{username}» eliminada.')
    return redirect('panel_usuarios')


# =============================================================================
# Temas (/panel/temas/) — RF-07
# =============================================================================


@solo_administrador
def panel_temas(request):
    """Alta de temas y conteo de trámites por tema."""
    if request.method == 'POST':
        form = TemaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Tema «{form.cleaned_data["nombre"]}» creado: ya aparece '
                'en los formularios de trámites.',
            )
            return redirect('panel_temas')
    else:
        form = TemaForm()

    temas = Tema.objects.annotate(cantidad=Count('tramites'))
    return render(request, 'panel/temas.html', {
        'form': form,
        'temas': temas,
    })
