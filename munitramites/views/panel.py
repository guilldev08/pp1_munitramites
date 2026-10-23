"""Panel propio de administración (/panel/). >>> ACÁ SE GESTIONA EL DÍA A DÍA <<<

El sitio tiene dos puertas distintas:

* **`/panel/`** — este módulo. Los roles de gestión trabajan acá: el
  *administrativo* con Centro de Trámites, Centro de Consultas y temas;
  el *administrador* hace todo eso y además las cuentas de usuarios; el
  superusuario entra a todo. Los roles son acumulativos (ver
  `models.Perfil.Rol`). Es el reemplazo amigable del /admin/ de Django.
* **`/admin/`** — Django a pelo, RESERVADO al superusuario (lo vigila
  `middleware.AdminSoloSuperusuario`). Sirve para lo que el panel no hace:
  organismos, municipios, grupos, perfiles y el resto de las tablas.

Reglas de este módulo (ESP-02 / RF-13):

* nadie entra sin sesión (lo manda `@login_required` al login),
* un ciudadano no pasa (mensaje claro y vuelta a la portada),
* la gestión de cuentas (/panel/usuarios/…) es solo del rol
  administrador y del superusuario (la vigila `solo_gestor_de_cuentas`),
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
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.http import require_POST

from ..forms import (
    EnlaceFormSet, RespuestaConsultaForm, RequisitoFormSet, TemaForm,
    TramitePanelForm, UsuarioPanelForm, UsuarioRolForm,
)
from ..models import (
    Consulta, Municipio, Organismo, Tema, Tramite, gestiona_cuentas,
)

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


def solo_gestor_de_cuentas(vista):
    """Decorador de /panel/usuarios/…: rol administrador o superusuario.

    El administrativo entra al panel pero no a las cuentas: ni la pestaña
    «Usuarios» se le muestra ni las URLs de esa sección le responden.
    """

    @login_required
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not gestiona_cuentas(request.user):
            messages.error(
                request,
                'La gestión de cuentas es solo para usuarios administradores '
                'del sitio. Si necesitás acceso, pedile al administrador.',
            )
            return redirect('panel')
        return vista(request, *args, **kwargs)

    return envuelta


# =============================================================================
# Dashboard (/panel/)
# =============================================================================


@solo_administrador
def panel(request):
    """Resumen general: contadores, gráficos y últimos movimientos."""
    consultas = Consulta.objects
    tramites_total = Tramite.objects.count()
    tramites_activos = Tramite.objects.filter(activo=True).count()
    pendientes = consultas.filter(estado=Consulta.Estado.PENDIENTE).count()
    consultas_total = consultas.count()

    def pct(parte, total):
        # Siempre enteros: un decimal con coma rompería el CSS de los gráficos
        return round(parte * 100 / total) if total else 0

    # Barras: los 6 temas con más trámites (alto 0-100 respecto del mayor)
    temas_top = list(
        Tema.objects.annotate(n=Count('tramites')).order_by('-n', 'nombre')[:6]
    )
    mayor = max([t.n for t in temas_top] or [0]) or 1
    grafico_temas = [
        {'nombre': t.nombre, 'n': t.n, 'alto': max(4, pct(t.n, mayor))}
        for t in temas_top
    ]

    # Anillo: consultas por estado (pendiente rojo, respondido verde, cerrado azul)
    colores = {
        Consulta.Estado.PENDIENTE: 'var(--m-rojo)',
        Consulta.Estado.RESPONDIDO: 'var(--m-verde)',
        Consulta.Estado.CERRADO: 'var(--m-azul)',
    }
    por_estado, tramos, desde = [], [], 0
    for valor, texto in Consulta.Estado.choices:
        n = consultas.filter(estado=valor).count()
        hasta = desde + pct(n, consultas_total)
        por_estado.append({'texto': texto, 'n': n, 'color': colores[valor]})
        tramos.append(f'{colores[valor]} {desde}% {hasta}%')
        desde = hasta
    if tramos:
        tramos[-1] = tramos[-1].rsplit(' ', 1)[0] + ' 100%'
    donut = (
        f"conic-gradient({', '.join(tramos)})" if consultas_total
        else 'conic-gradient(var(--s-ln) 0 100%)'
    )

    # Barras de progreso: trámites por modalidad
    por_modalidad = [
        {
            'texto': texto,
            'n': (n := Tramite.objects.filter(modalidad=valor).count()),
            'pct': pct(n, tramites_total),
        }
        for valor, texto in Tramite.Modalidad.choices
    ]

    contexto = {
        'tramites_total': tramites_total,
        'tramites_activos': tramites_activos,
        'destacados': Tramite.objects.filter(destacado=True, activo=True).count(),
        'pct_activos': pct(tramites_activos, tramites_total),
        'pendientes': pendientes,
        'pct_pendientes': pct(pendientes, consultas_total),
        'consultas_total': consultas_total,
        'usuarios': User.objects.filter(is_active=True).count(),
        'temas': Tema.objects.count(),
        'grafico_temas': grafico_temas,
        'por_estado': por_estado,
        'donut': donut,
        'por_modalidad': por_modalidad,
        'ultimas_consultas': consultas.select_related(
            'usuario', 'tramite'
        ).order_by('-fecha')[:5],
        'ultimos_tramites': Tramite.objects.select_related(
            'tema', 'municipio'
        ).order_by('-creado')[:5],
    }
    return render(request, 'panel/dashboard.html', contexto)


# =============================================================================
# Centro de Trámites (/panel/tramites/)
# =============================================================================


# Ordenes permitidos del listado: un whitelist, para que ?orden= no pase
# cualquier columna a la base.
ORDENES_TRAMITE = {
    'titulo': 'titulo', '-titulo': '-titulo',
    'tema': 'tema__nombre', '-tema': '-tema__nombre',
    'modalidad': 'modalidad', '-modalidad': '-modalidad',
    'municipio': 'municipio__nombre', '-municipio': '-municipio__nombre',
    'destacado': 'destacado', '-destacado': '-destacado',
    'activo': 'activo', '-activo': '-activo',
    'creado': 'creado', '-creado': '-creado',
}

# Acciones del listado, masivas (marcando checkboxes) o de una fila
# (los botones de la última columna). Las mismas que el /admin/.
ACCIONES_TRAMITE = {
    'activar': {'activo': True},
    'desactivar': {'activo': False},
    'destacar': {'destacado': True},
    'quitar_destacado': {'destacado': False},
}


def _filtros_tramites(request, queryset):
    """Buscador + filtros laterales del listado (?q=, ?estado=, ?tema=…)."""
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(titulo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(organismo__nombre__icontains=q)
            | Q(municipio__nombre__icontains=q)
        )

    estado = request.GET.get('estado', '')
    if estado == 'activos':
        queryset = queryset.filter(activo=True)
    elif estado == 'inactivos':
        queryset = queryset.filter(activo=False)

    for parametro, campo in (
        ('tema', 'tema_id'), ('municipio', 'municipio_id'),
        ('organismo', 'organismo_id'),
    ):
        valor = request.GET.get(parametro, '')
        if valor.isdigit():
            queryset = queryset.filter(**{campo: valor})

    modalidad = request.GET.get('modalidad', '')
    if modalidad in dict(Tramite.Modalidad.choices):
        queryset = queryset.filter(modalidad=modalidad)

    destacado = request.GET.get('destacado', '')
    if destacado in ('si', 'no'):
        queryset = queryset.filter(destacado=(destacado == 'si'))

    orden = ORDENES_TRAMITE.get(request.GET.get('orden', ''))
    if orden:
        return queryset.order_by(orden)
    return queryset.order_by('-destacado', 'titulo')


@solo_administrador
def panel_tramites(request):
    """Listado de trámites con la estructura del changelist del /admin/.

    Buscador arriba, filtros laterales (estado, tema, modalidad,
    municipio, organismo y destacado), columnas ordenables, checkboxes
    para marcar filas y acciones masivas. Sin dependencias de JS: todo
    son GET y POST normales.
    """
    queryset = _filtros_tramites(
        request,
        Tramite.objects.select_related('tema', 'municipio', 'organismo'),
    )

    paginador = Paginator(queryset, POR_PAGINA)
    return render(request, 'panel/tramites_lista.html', {
        'pagina': paginador.get_page(request.GET.get('pagina')),
        'q': request.GET.get('q', '').strip(),
        'estado': request.GET.get('estado', ''),
        'tema_id': request.GET.get('tema', ''),
        'modalidad': request.GET.get('modalidad', ''),
        'municipio_id': request.GET.get('municipio', ''),
        'organismo_id': request.GET.get('organismo', ''),
        'destacado': request.GET.get('destacado', ''),
        'orden': request.GET.get('orden', ''),
        'hay_filtros': any(request.GET.get(c) for c in (
            'q', 'estado', 'tema', 'modalidad', 'municipio', 'organismo',
            'destacado', 'orden',
        )),
        'temas': Tema.objects.order_by('nombre'),
        'municipios': Municipio.objects.order_by('nombre'),
        'organismos': Organismo.objects.order_by('nombre'),
        'modalidades': Tramite.Modalidad.choices,
    })


@solo_administrador
@require_POST
def panel_tramites_accion(request):
    """Acciones del listado: masivas (checkboxes) o de una sola fila.

    Los botones de fila viajan como `fila_<pk>=<accion>` dentro del
    MISMO formulario que los checkboxes, así la tabla no tiene
    formularios anidados. `siguiente` es la URL de vuelta (con los
    filtros puestos); si no confía, se vuelve al listado limpio.
    """
    destino = request.POST.get('siguiente', '')
    if not destino.startswith(reverse('panel_tramites')):
        destino = reverse('panel_tramites')

    fila = next((k for k in request.POST if k.startswith('fila_')), '')
    if fila:
        accion = request.POST.get(fila, '')
        try:
            pks = [int(fila.split('_', 1)[1])]
        except ValueError:
            pks = []
    else:
        accion = request.POST.get('accion', '')
        pks = [pk for pk in request.POST.getlist('seleccion') if pk.isdigit()]

    if not (pks and accion in ACCIONES_TRAMITE):
        messages.error(
            request, 'Elegí una acción y marcá al menos un trámite.'
        )
        return redirect(destino)

    actualizados = Tramite.objects.filter(pk__in=pks).update(
        **ACCIONES_TRAMITE[accion]
    )
    plural = '' if actualizados == 1 else 's'
    messages.success(
        request, f'{actualizados} trámite{plural} actualizado{plural}.'
    )
    return redirect(destino)


def _crear_relaciones_nuevas(post):
    """Crea municipio/organismo «sobre la marcha» si el form los pide.

    El formulario del Centro de Trámites trae, debajo de cada select,
    un campo `municipio_nuevo` / `organismo_nuevo`. Si trae texto, se
    crea (o se reusa el existente) y la FK queda seteada: no hace falta
    salirse a cargarlo en otra pantalla. Devuelve el POST pisado.
    """
    data = post.copy()
    for campo, modelo, extras in (
        ('municipio', Municipio, {}),
        # Organismo además pide dirección: a nivel DB acepta string
        # vacío, pero dejamos una aclaración legible para el /admin/.
        ('organismo', Organismo, {'direccion': 'Sin dirección informada'}),
    ):
        nombre = data.get(f'{campo}_nuevo', '').strip()
        if nombre:
            obj, _ = modelo.objects.get_or_create(nombre=nombre, defaults=extras)
            data[campo] = obj.pk
    return data


def _contexto_form_tramite(request, tramite):
    """Form + inlines (requisitos y enlaces) para GET o POST."""
    if request.method == 'POST':
        form = TramitePanelForm(
            _crear_relaciones_nuevas(request.POST), instance=tramite
        )
        requisitos = RequisitoFormSet(request.POST, instance=tramite)
        enlaces = EnlaceFormSet(request.POST, instance=tramite)
    else:
        form = TramitePanelForm(instance=tramite)
        requisitos = RequisitoFormSet(instance=tramite)
        enlaces = EnlaceFormSet(instance=tramite)
    return form, requisitos, enlaces


# Los «orden» se renumeran pasando primero por este rango: así nunca se
# viola la restricción única (trámite, orden) a mitad de camino.
_ORDEN_TEMPORAL = 1_000_000


def _guardar_inlines(formset):
    """Guarda las filas del formset numerando «orden» por su posición.

    El usuario no escribe el orden: es el de las filas, de arriba hacia
    abajo. Se hace en dos pasos para no violar nunca la restricción única
    (trámite, orden): primero las filas que ya existen se corren a un
    rango temporal y recién después se numera 0, 1, 2… en el orden del
    formulario.
    """
    # Crea/actualiza en memoria y junta las filas marcadas para borrar.
    formset.save(commit=False)
    for borrado in formset.deleted_objects:
        borrado.delete()

    filas = [
        form for form in formset.forms
        if not form.cleaned_data.get('DELETE')
        and (form.instance.pk or form.has_changed())
    ]

    # Paso 1: los que ya están en la base pasan al rango temporal.
    for i, form in enumerate(filas):
        obj = form.instance
        if obj.pk:
            obj.orden = _ORDEN_TEMPORAL + i
            obj.save()

    # Paso 2: numeración definitiva por posición (acá se crean los nuevos).
    for i, form in enumerate(filas):
        obj = form.instance
        obj.orden = i
        obj.save()


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
    _guardar_inlines(requisitos)
    enlaces.instance = tramite
    _guardar_inlines(enlaces)
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
    """Etiqueta corta del rol para los mensajes del panel.

    Nunca se tilda el superusuario: está fuera de los tres roles.
    """
    if user.is_superuser:
        return 'Superusuario'
    perfil = getattr(user, 'perfil', None)
    if perfil is not None:
        return perfil.get_rol_display()
    # Cuenta vieja sin perfil: is_staff es el espejo del rol
    return 'Administrativo' if user.is_staff else 'Corriente'


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
@solo_gestor_de_cuentas
def panel_usuarios(request):
    """Listado de cuentas con búsqueda (rol administrador o super)."""
    queryset = User.objects.select_related('perfil').order_by('username')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        queryset = queryset.filter(
            Q(username__icontains=busqueda) | Q(email__icontains=busqueda)
        )

    paginador = Paginator(queryset, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('pagina'))
    return render(request, 'panel/usuarios_lista.html', {
        'pagina': pagina,
        'q': busqueda,
    })


@solo_administrador
@solo_gestor_de_cuentas
def panel_usuario_nuevo(request):
    """Alta de cuentas con cualquiera de los tres roles. Nunca superuser."""
    if request.method == 'POST':
        form = UsuarioPanelForm(request.POST)
        if form.is_valid():
            user = form.save()
            rol = user.perfil.get_rol_display()
            if user.is_staff:
                messages.success(
                    request,
                    f'Cuenta «{user.username}» creada con rol {rol}: '
                    'ya puede entrar al panel.',
                )
            else:
                messages.success(
                    request,
                    f'Cuenta «{user.username}» creada (rol {rol}).',
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
@solo_gestor_de_cuentas
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
                f'Cuenta «{user.username}» actualizada: rol {_rol(user)}.',
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
@solo_gestor_de_cuentas
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
