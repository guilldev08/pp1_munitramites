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

from datetime import timedelta, timezone as dt_timezone
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from ..forms import (
    ArchivoFormSet, DireccionFormSet, EnlaceFormSet, RespuestaConsultaForm,
    RequisitoFormSet, RespuestaTicketForm, TemaForm, TicketForm,
    TramitePanelForm, UsuarioPanelForm, UsuarioRolForm,
)
from ..models import (
    Consulta, Municipio, Organismo, Tema, Tramite, gestiona_cuentas,
    puede_gestionar_tickets, usa_tickets, AdjuntoTicket, Ticket,
)
from ..services.busqueda import buscar_tramites

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

    El administrativo entra al panel pero no a las cuentas: ni el ítem
    «Usuarios» del menú se le muestra ni las URLs de esa sección le
    responden.
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
# Tickets internos (dashboard y /panel/tickets/)
# =============================================================================


def _tickets_visibles(user):
    """Tickets que puede ver la cuenta.

    El administrador y el superusuario ven todos; el administrativo, solo
    los suyos.
    """
    queryset = (
        Ticket.objects
        .select_related('creado_por', 'respondido_por')
        .prefetch_related('adjuntos')
    )
    if puede_gestionar_tickets(user):
        return queryset
    return queryset.filter(creado_por=user)


def _puede_ver_ticket(user, ticket):
    """¿Puede abrir este ticket? (su dueño, o quien los gestiona)."""
    return puede_gestionar_tickets(user) or ticket.creado_por_id == user.pk


def _crear_ticket(request, form):
    """Crea el ticket con sus adjuntos y devuelve el objeto."""
    ticket = Ticket.objects.create(
        asunto=form.cleaned_data['asunto'],
        descripcion=form.cleaned_data['descripcion'],
        creado_por=request.user,
    )
    for archivo in form.cleaned_data['archivos']:
        AdjuntoTicket.objects.create(
            ticket=ticket, archivo=archivo, nombre=archivo.name,
        )
    return ticket


# =============================================================================
# Dashboard (/panel/)
# =============================================================================


# Períodos que ofrece el selector del tablero. El valor es la cantidad
# de días hacia atrás (None = sin límite).
PERIODOS_DASHBOARD = (
    ('7d', 'Últimos 7 días', 7),
    ('30d', 'Últimos 30 días', 30),
    ('3m', 'Últimos 3 meses', 90),
    ('6m', 'Últimos 6 meses', 180),
    ('todo', 'Todo el período', None),
)
_PERIODOS = {
    clave: (texto, dias) for clave, texto, dias in PERIODOS_DASHBOARD
}

NOMBRES_MES = (
    'ene', 'feb', 'mar', 'abr', 'may', 'jun',
    'jul', 'ago', 'sep', 'oct', 'nov', 'dic',
)


def _pct(parte, total):
    """Porcentaje entero: con decimales se rompería el CSS de los gráficos."""
    return round(parte * 100 / total) if total else 0


def _fecha_local(valor):
    """Pasa un datetime de Firebird (naive, en UTC) a la hora local."""
    if valor is None:
        return None
    if timezone.is_naive(valor):
        valor = timezone.make_aware(valor, dt_timezone.utc)
    return timezone.localtime(valor)


def _filtros_dashboard(request):
    """Lee y normaliza los filtros del tablero (?periodo=, ?desde=…).

    Devuelve las fechas ya resueltas en hora local para poder comparar
    los registros sin depender de funciones de fecha de Firebird.
    """
    get = request.GET
    periodo = get.get('periodo', '30d')
    if periodo not in _PERIODOS:
        periodo = '30d'

    desde = parse_date((get.get('desde') or '').strip())
    hasta = parse_date((get.get('hasta') or '').strip())
    personalizado = bool(desde or hasta)
    if personalizado:
        periodo = 'personalizado'
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde

    municipio_id = get.get('municipio', '')
    municipio_id = int(municipio_id) if municipio_id.isdigit() else None

    estado = get.get('estado', '')
    if estado not in dict(Consulta.Estado.choices):
        estado = ''

    modalidad = get.get('modalidad', '')
    if modalidad not in dict(Tramite.Modalidad.choices):
        modalidad = ''

    hoy = timezone.localdate()
    if personalizado:
        inicio = desde
        fin = hasta or hoy
        if inicio and inicio > fin:
            inicio, fin = fin, inicio
    else:
        dias = _PERIODOS[periodo][1]
        inicio = hoy - timedelta(days=dias - 1) if dias else None
        fin = hoy if dias else None

    if personalizado:
        if inicio and fin:
            etiqueta = f'{inicio:%d/%m/%Y} – {fin:%d/%m/%Y}'
        elif inicio:
            etiqueta = f'Desde {inicio:%d/%m/%Y}'
        else:
            etiqueta = f'Hasta {fin:%d/%m/%Y}'
    else:
        etiqueta = _PERIODOS[periodo][0]

    return {
        'periodo': periodo,
        'personalizado': personalizado,
        'desde': desde,
        'hasta': hasta,
        'inicio': inicio,
        'fin': fin,
        'etiqueta': etiqueta,
        'municipio_id': municipio_id,
        'estado': estado,
        'modalidad': modalidad,
    }


def _en_periodo(fecha, filtros):
    """¿La fecha (UTC naive de Firebird) cae dentro del período elegido?"""
    local = _fecha_local(fecha)
    if local is None:
        return False
    dia = local.date()
    if filtros['inicio'] and dia < filtros['inicio']:
        return False
    if filtros['fin'] and dia > filtros['fin']:
        return False
    return True


def _consultas_del_dashboard(filtros):
    """Consultas que entran en los filtros de municipio y modalidad."""
    queryset = Consulta.objects.select_related(
        'usuario', 'tramite__municipio', 'tramite__tema', 'respondido_por',
    )
    if filtros['municipio_id']:
        queryset = queryset.filter(
            Q(tramite__municipio_id=filtros['municipio_id'])
            | Q(tramite__municipios__pk=filtros['municipio_id'])
        ).distinct()
    if filtros['modalidad']:
        queryset = queryset.filter(tramite__modalidad=filtros['modalidad'])
    return list(queryset)


def _tramites_del_dashboard(filtros):
    """Trámites que entran en los filtros de municipio y modalidad."""
    queryset = Tramite.objects.select_related('tema', 'municipio')
    if filtros['municipio_id']:
        queryset = queryset.filter(
            Q(municipio_id=filtros['municipio_id'])
            | Q(municipios__pk=filtros['municipio_id'])
            | Q(direcciones__municipio_id=filtros['municipio_id'])
        ).distinct()
    if filtros['modalidad']:
        queryset = queryset.filter(modalidad=filtros['modalidad'])
    return list(queryset)


def _agrupar_consultas(consultas, filtros):
    """Arma la serie de «consultas por período».

    Con rangos cortos agrupa por día y con rangos largos por mes. Los
    huecos sin consultas se rellenan con cero para que la línea no
    invente continuidad entre dos fechas lejanas.
    """
    fechas = [_fecha_local(c.fecha).date() for c in consultas]
    if not fechas:
        return {'puntos': [], 'linea': '', 'area': '', 'total': 0}

    inicio = filtros['inicio'] or min(fechas)
    fin = filtros['fin'] or max(fechas)
    if inicio > fin:
        inicio, fin = fin, inicio

    por_mes = (fin - inicio).days > 62
    claves = []
    if por_mes:
        anio, mes = inicio.year, inicio.month
        while (anio, mes) <= (fin.year, fin.month):
            claves.append((anio, mes))
            mes += 1
            if mes == 13:
                mes = 1
                anio += 1
        etiquetas = [
            f'{NOMBRES_MES[mes - 1]} {anio}' for anio, mes in claves
        ]
        conteo = {clave: 0 for clave in claves}
        for fecha in fechas:
            clave = (fecha.year, fecha.month)
            if clave in conteo:
                conteo[clave] += 1
        valores = [conteo[clave] for clave in claves]
    else:
        dia = inicio
        while dia <= fin:
            claves.append(dia)
            dia += timedelta(days=1)
        etiquetas = [f'{d:%d/%m}' for d in claves]
        conteo = {clave: 0 for clave in claves}
        for fecha in fechas:
            if fecha in conteo:
                conteo[fecha] += 1
        valores = [conteo[clave] for clave in claves]

    if not valores:
        return {'puntos': [], 'linea': '', 'area': '', 'total': 0}

    ancho, base, techo = 640, 170, 18
    maximo = max(valores) or 1
    n = len(valores)
    paso = (ancho - 24) / (n - 1) if n > 1 else 0
    puntos = []
    for i, valor in enumerate(valores):
        x = 12 + i * paso if n > 1 else ancho / 2
        y = base - (valor / maximo) * (base - techo)
        puntos.append({
            'x': round(x, 1),
            'y': round(y, 1),
            'n': valor,
            'etiqueta': etiquetas[i],
        })

    linea = ' '.join(
        f'{"M" if i == 0 else "L"} {p["x"]} {p["y"]}'
        for i, p in enumerate(puntos)
    )
    area = (
        f'M {puntos[0]["x"]} {base} '
        + ' '.join(f'L {p["x"]} {p["y"]}' for p in puntos)
        + f' L {puntos[-1]["x"]} {base} Z'
    )
    return {
        'puntos': puntos,
        'linea': linea,
        'area': area,
        'total': sum(valores),
        'maximo': maximo,
        'base': base,
        'eje_inicio': etiquetas[0],
        'eje_fin': etiquetas[-1],
        'por_mes': por_mes,
    }


def _formato_duracion(delta):
    """Duración breve en español: «2 h 15 min», «1 d 4 h», «8 min»."""
    segundos = max(0, int(delta.total_seconds()))
    dias, resto = divmod(segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos = resto // 60
    if dias:
        return f'{dias} d {horas} h'
    if horas:
        return f'{horas} h {minutos} min'
    return f'{minutos} min'


def _actividad_reciente(consultas, tramites, tickets, filtros):
    """Mezcla los movimientos reales de consultas, trámites y tickets.

    No hay tabla de auditoría: cada evento sale de una fecha que el
    sistema ya guarda (alta, modificación o respuesta). Lo que no tiene
    fecha confiable no se muestra.
    """
    eventos = []

    def agregar(tipo, fecha, texto, url, usuario='', color='azul'):
        local = _fecha_local(fecha)
        if local is None:
            return
        eventos.append({
            'tipo': tipo,
            'fecha': local,
            'texto': texto,
            'url': url,
            'usuario': usuario or '',
            'color': color,
        })

    for c in consultas:
        agregar(
            'consulta', c.fecha,
            f'Nueva consulta: «{c.asunto}»',
            reverse('panel_consulta', args=[c.pk]),
            c.usuario.username if c.usuario else 'Anónimo',
            'rojo',
        )
        if c.fecha_respuesta:
            agregar(
                'respuesta', c.fecha_respuesta,
                f'Consulta respondida: «{c.asunto}»',
                reverse('panel_consulta', args=[c.pk]),
                c.respondido_por.username if c.respondido_por else 'Staff',
                'verde',
            )

    for t in tramites:
        agregar(
            'tramite', t.creado,
            f'Trámite publicado: «{t.titulo}»',
            reverse('panel_tramite_editar', args=[t.pk]),
            color='azul',
        )
        creado = _fecha_local(t.creado)
        actualizado = _fecha_local(t.actualizado)
        if (
            creado and actualizado
            and (actualizado - creado).total_seconds() > 60
            and _en_periodo(t.actualizado, filtros)
        ):
            agregar(
                'tramite', t.actualizado,
                f'Trámite actualizado: «{t.titulo}»',
                reverse('panel_tramite_editar', args=[t.pk]),
                color='azul',
            )

    for tk in tickets:
        if not _en_periodo(tk.fecha, filtros):
            continue
        agregar(
            'ticket', tk.fecha,
            f'Ticket #{tk.pk} creado: «{tk.asunto}»',
            reverse('panel_ticket_detalle', args=[tk.pk]),
            tk.creado_por.username if tk.creado_por else '',
            'azul',
        )
        if tk.fecha_respuesta and _en_periodo(tk.fecha_respuesta, filtros):
            agregar(
                'ticket', tk.fecha_respuesta,
                f'Ticket #{tk.pk} respondido: «{tk.asunto}»',
                reverse('panel_ticket_detalle', args=[tk.pk]),
                tk.respondido_por.username if tk.respondido_por else '',
                'verde',
            )

    # Solo los movimientos del período elegido, del más nuevo al más viejo.
    eventos = [e for e in eventos if _en_periodo(e['fecha'], filtros)]
    eventos.sort(key=lambda e: e['fecha'], reverse=True)
    return eventos[:8]


def _contexto_dashboard(request):
    """Calcula todo el tablero a partir de los datos reales de Firebird.

    Limitaciones conocidas y documentadas (no se inventan valores):

    * **Consultas por municipio**: la consulta no guarda municipio propio.
      Se usa el municipio del trámite asociado; las consultas sin trámite
      quedan en «Sin municipio asociado».
    * **Tiempo promedio de respuesta**: se mide desde la migración 0018,
      que agregó `Consulta.fecha_respuesta`. Las respuestas anteriores no
      tienen el dato y quedan fuera del promedio.
    * **Trámites desactualizados**: `actualizado` cambia con cualquier
      edición, pero no alcanza para afirmar que el contenido está
      desactualizado. El indicador queda fuera hasta tener una fecha de
      revisión confiable.
    """
    filtros = _filtros_dashboard(request)
    consultas_scope = _consultas_del_dashboard(filtros)
    consultas_periodo = [
        c for c in consultas_scope if _en_periodo(c.fecha, filtros)
    ]
    consultas_filtradas = [
        c for c in consultas_periodo
        if not filtros['estado'] or c.estado == filtros['estado']
    ]
    tramites = _tramites_del_dashboard(filtros)

    # --- Indicadores principales -----------------------------------------
    tramites_total = len(tramites)
    tramites_activos = sum(1 for t in tramites if t.activo)
    tramites_inactivos = tramites_total - tramites_activos
    consultas_total = len(consultas_periodo)
    pendientes = sum(
        1 for c in consultas_periodo
        if c.estado == Consulta.Estado.PENDIENTE
    )
    tickets = list(_tickets_visibles(request.user))
    tickets_pendientes = sum(
        1 for t in tickets if t.estado == Ticket.Estado.ABIERTO
    )

    # --- Tiempo promedio de respuesta ------------------------------------
    # Solo cuentan las consultas respondidas desde que se guarda
    # `fecha_respuesta`; las viejas no tienen ese dato y no se inventa.
    duraciones = []
    for c in consultas_periodo:
        if not c.fecha_respuesta:
            continue
        alta = _fecha_local(c.fecha)
        respuesta = _fecha_local(c.fecha_respuesta)
        if alta and respuesta and respuesta >= alta:
            duraciones.append(respuesta - alta)
    promedio_respuesta = (
        _formato_duracion(sum(duraciones, timedelta()) / len(duraciones))
        if duraciones else ''
    )

    # --- Consultas por estado (anillo) -----------------------------------
    colores = {
        Consulta.Estado.PENDIENTE: 'var(--m-rojo)',
        Consulta.Estado.RESPONDIDO: 'var(--m-verde)',
        Consulta.Estado.CERRADO: 'var(--m-azul)',
    }
    por_estado, tramos, desde = [], [], 0
    for valor, texto in Consulta.Estado.choices:
        n = sum(1 for c in consultas_filtradas if c.estado == valor)
        hasta = desde + _pct(n, len(consultas_filtradas))
        por_estado.append({
            'valor': valor, 'texto': texto, 'n': n, 'color': colores[valor],
        })
        tramos.append(f'{colores[valor]} {desde}% {hasta}%')
        desde = hasta
    if tramos:
        tramos[-1] = tramos[-1].rsplit(' ', 1)[0] + ' 100%'
    donut = (
        f"conic-gradient({', '.join(tramos)})" if consultas_filtradas
        else 'conic-gradient(var(--s-ln) 0 100%)'
    )

    # --- Trámites más consultados ----------------------------------------
    ranking = {}
    for c in consultas_filtradas:
        if not c.tramite_id:
            continue
        fila = ranking.setdefault(c.tramite_id, {
            'pk': c.tramite_id,
            'titulo': c.tramite.titulo,
            'n': 0,
        })
        fila['n'] += 1
    ranking = sorted(
        ranking.values(), key=lambda f: (-f['n'], f['titulo'])
    )[:6]

    # --- Consultas por municipio (según el trámite asociado) -------------
    municipios_conteo = {}
    for c in consultas_filtradas:
        if c.tramite_id and c.tramite.municipio_id:
            clave = (c.tramite.municipio.nombre, c.tramite.municipio_id)
        else:
            clave = ('Sin municipio asociado', None)
        municipios_conteo[clave] = municipios_conteo.get(clave, 0) + 1
    por_municipio = [
        {'nombre': nombre, 'pk': pk, 'n': n}
        for (nombre, pk), n in sorted(
            municipios_conteo.items(), key=lambda par: (-par[1], par[0][0])
        )[:6]
    ]
    mayor_municipio = max([m['n'] for m in por_municipio] or [0]) or 1
    for m in por_municipio:
        m['alto'] = max(4, _pct(m['n'], mayor_municipio))

    # --- Trámites por tema y por modalidad -------------------------------
    temas_conteo = {}
    for t in tramites:
        nombre = t.tema.nombre if t.tema_id else 'Sin tema'
        clave = (nombre, t.tema_id)
        temas_conteo[clave] = temas_conteo.get(clave, 0) + 1
    temas_top = sorted(
        temas_conteo.items(), key=lambda par: (-par[1], par[0][0])
    )[:6]
    mayor_tema = max([n for _, n in temas_top] or [0]) or 1
    grafico_temas = [
        {
            'nombre': nombre, 'pk': pk, 'n': n,
            'alto': max(4, _pct(n, mayor_tema)),
        }
        for (nombre, pk), n in temas_top
    ]

    modalidad_conteo = {}
    for t in tramites:
        modalidad_conteo[t.modalidad] = (
            modalidad_conteo.get(t.modalidad, 0) + 1
        )
    por_modalidad = [
        {
            'valor': valor,
            'texto': texto,
            'n': (n := modalidad_conteo.get(valor, 0)),
            'pct': _pct(n, tramites_total),
        }
        for valor, texto in Tramite.Modalidad.choices
    ]

    contexto = {
        # Indicadores
        'tramites_total': tramites_total,
        'tramites_activos': tramites_activos,
        'tramites_inactivos': tramites_inactivos,
        'destacados': sum(1 for t in tramites if t.activo and t.destacado),
        'pct_activos': _pct(tramites_activos, tramites_total),
        'consultas_total': consultas_total,
        'pendientes': pendientes,
        'consultas_pendientes': pendientes,
        'pct_pendientes': _pct(pendientes, consultas_total),
        'usuarios': User.objects.filter(is_staff=False).count(),
        'temas': Tema.objects.count(),
        'tickets_total': len(tickets),
        'tickets_pendientes': tickets_pendientes,
        'promedio_respuesta': promedio_respuesta,
        'respuestas_medidas': len(duraciones),
        # Gráficos
        'serie_consultas': _agrupar_consultas(consultas_filtradas, filtros),
        'por_estado': por_estado,
        'donut': donut,
        'consultas_grafico_total': len(consultas_filtradas),
        'ranking': ranking,
        'por_municipio': por_municipio,
        'grafico_temas': grafico_temas,
        'por_modalidad': por_modalidad,
        # Actividad
        'actividad': _actividad_reciente(
            consultas_filtradas, tramites, tickets, filtros,
        ),
        # Filtros
        'filtros': filtros,
        'periodos': PERIODOS_DASHBOARD,
        'municipios': Municipio.objects.order_by('nombre'),
        'estados_consulta': Consulta.Estado.choices,
        'modalidades': Tramite.Modalidad.choices,
        'hay_filtros': bool(
            filtros['personalizado'] or filtros['periodo'] != '30d'
            or filtros['municipio_id'] or filtros['estado']
            or filtros['modalidad']
        ),
    }
    return contexto


@solo_administrador
def panel(request):
    """Resumen general: contadores, gráficos y últimos movimientos."""
    return render(
        request, 'panel/dashboard.html', _contexto_dashboard(request)
    )


@solo_administrador
def panel_dashboard_datos(request):
    """Solo el contenido del tablero, para refrescarlo sin recargar.

    El formulario de filtros lo pide por fetch; sin JavaScript cae en
    `panel` con los mismos parámetros por GET. Los permisos se validan
    igual que en la página completa.
    """
    return render(
        request, 'panel/_dashboard_contenido.html', _contexto_dashboard(request)
    )


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

    estado = request.GET.get('estado', '')
    if estado == 'activos':
        queryset = queryset.filter(activo=True)
    elif estado == 'inactivos':
        queryset = queryset.filter(activo=False)

    for parametro, campo in (
        ('tema', 'tema_id'), ('organismo', 'organismo_id'),
    ):
        valor = request.GET.get(parametro, '')
        if valor.isdigit():
            queryset = queryset.filter(**{campo: valor})

    municipio_id = request.GET.get('municipio', '')
    if municipio_id.isdigit():
        # El municipio principal, cualquiera de los otros municipios
        # marcados o cualquiera de las sedes del trámite.
        queryset = queryset.filter(
            Q(municipio_id=municipio_id)
            | Q(municipios__pk=municipio_id)
            | Q(direcciones__municipio_id=municipio_id)
        ).distinct()

    modalidad = request.GET.get('modalidad', '')
    if modalidad in dict(Tramite.Modalidad.choices):
        queryset = queryset.filter(modalidad=modalidad)

    destacado = request.GET.get('destacado', '')
    if destacado in ('si', 'no'):
        queryset = queryset.filter(destacado=(destacado == 'si'))

    orden = ORDENES_TRAMITE.get(request.GET.get('orden', ''))
    if orden:
        queryset = queryset.order_by(orden)
    else:
        queryset = queryset.order_by('-destacado', 'titulo')

    # La búsqueda flexible va al final: ordena por relevancia (tolera
    # tildes, mayúsculas, plurales, palabras parciales y sinónimos).
    if q:
        queryset = buscar_tramites(queryset, q)
    return queryset


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
        Tramite.objects
        .select_related('tema', 'municipio', 'organismo')
        .prefetch_related('direcciones__municipio', 'requisitos'),
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

    El formulario del Centro de Trámites trae, debajo de cada lista, un
    campo `municipio_nuevo` / `organismo_nuevo`. Si trae texto, se crea
    (o se reusa el existente): para el municipio se agrega a la selección
    (queda primero de la lista alfabética, así es el principal) y para el
    organismo la FK queda seteada. No hace falta salirse a cargarlo en
    otra pantalla. Devuelve el POST pisado.
    """
    data = post.copy()
    for campo, modelo, extras in (
        ('organismo', Organismo, {
            'direccion': 'Sin dirección informada',
        }),
    ):
        nombre = data.get(f'{campo}_nuevo', '').strip()
        if nombre:
            obj, _ = modelo.objects.get_or_create(nombre=nombre, defaults=extras)
            data[campo] = obj.pk

    nombre = data.get('municipio_nuevo', '').strip()
    if nombre:
        obj, _ = Municipio.objects.get_or_create(nombre=nombre)
        data.appendlist('municipios', str(obj.pk))
    return data


def _contexto_form_tramite(request, tramite):
    """Form + inlines (requisitos, enlaces, direcciones y archivos)."""
    if request.method == 'POST':
        form = TramitePanelForm(
            _crear_relaciones_nuevas(request.POST), instance=tramite
        )
        # Solo se consideran VINCULADOS los formsets cuyas claves viajaron
        # en el POST: así los envíos viejos (o tests) sin una sección no
        # generan «management form missing» ni tocan esas filas.
        if 'requisitos-TOTAL_FORMS' in request.POST:
            requisitos = RequisitoFormSet(request.POST, instance=tramite)
        else:
            requisitos = RequisitoFormSet(instance=tramite)
        if 'enlaces-TOTAL_FORMS' in request.POST:
            enlaces = EnlaceFormSet(request.POST, instance=tramite)
        else:
            enlaces = EnlaceFormSet(instance=tramite)
        if 'direcciones-TOTAL_FORMS' in request.POST:
            direcciones = DireccionFormSet(request.POST, instance=tramite)
        else:
            # POST de una versión anterior del formulario (o de un test):
            # se muestra el inline vacío, pero no se borran las direcciones
            # que ya estén guardadas.
            direcciones = DireccionFormSet(instance=tramite)
        if 'archivos-TOTAL_FORMS' in request.POST:
            archivos = ArchivoFormSet(
                request.POST, request.FILES, instance=tramite
            )
        else:
            # Igual que con las direcciones: un POST viejo no borra los
            # archivos ya cargados.
            archivos = ArchivoFormSet(instance=tramite)
    else:
        form = TramitePanelForm(instance=tramite)
        requisitos = RequisitoFormSet(instance=tramite)
        enlaces = EnlaceFormSet(instance=tramite)
        direcciones = DireccionFormSet(instance=tramite)
        archivos = ArchivoFormSet(instance=tramite)
    return form, requisitos, enlaces, direcciones, archivos


# Los «orden» se renumeran pasando primero por este rango: así nunca se
# viola la restricción única (trámite, orden) a mitad de camino.
_ORDEN_TEMPORAL = 1_000_000


def _hay_filas(formset):
    """¿Queda al menos una fila con datos en el formset?

    Cuentan las filas guardadas y las recién escritas; no cuentan las
    marcadas «Eliminar» ni las vacías (las que Django ignora al validar).
    """
    for form in formset.forms:
        if not form.is_bound:
            continue
        datos = getattr(form, 'cleaned_data', None) or {}
        if datos.get('DELETE'):
            continue
        if form.instance.pk or form.has_changed():
            return True
    return False


# Validación por modalidad (SPEC 2026-11): Virtual/Mixta exigen enlaces
# oficiales y Presencial/Mixta exigen direcciones de atención.
_REQUIERE_ENLACES = (
    Tramite.Modalidad.VIRTUAL, Tramite.Modalidad.MIXTA,
)
_REQUIERE_DIRECCIONES = (
    Tramite.Modalidad.PRESENCIAL, Tramite.Modalidad.MIXTA,
)
_CONDICIONES = [
    (
        _REQUIERE_ENLACES,
        'enlaces',
        'Con la modalidad «{nombre}» hay que cargar al menos un enlace '
        'oficial.',
    ),
    (
        _REQUIERE_DIRECCIONES,
        'direcciones',
        'Con la modalidad «{nombre}» hay que cargar al menos una dirección '
        'de atención.',
    ),
]


def _validar_condiciones_de_modalidad(form, formsets):
    """Exigencias de la modalidad elegida (SPEC 2026-11, sección 5.3).

    Se llama con `form` ya validado. Con modalidad Virtual o Mixta exige
    al menos un enlace oficial; con Presencial o Mixta, al menos una
    dirección de atención. SOLO mira formsets que hayan viajado en el
    POST (is_bound): así los envíos viejos sin esas claves no aparecen
    como «sección vacía» y el formulario por etapas, que siempre manda
    todas las secciones, sí queda sujeto a la exigencia. Si falta algo,
    agrega el error al form para que el formulario vuelva a mostrarse en
    pantalla y nada se guarde.
    """
    modalidad = form.cleaned_data['modalidad']
    nombre = dict(Tramite.Modalidad.choices)[modalidad]
    for modalidades, clave_formset, patron_mensaje in _CONDICIONES:
        if modalidad not in modalidades:
            continue
        formset = formsets[clave_formset]
        if not formset.is_bound:
            continue
        if not _hay_filas(formset):
            form.add_error(
                None, patron_mensaje.format(nombre=nombre)
            )


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
    después los requisitos, los enlaces, las direcciones y los archivos,
    igual que hace el /admin/.
    """
    form, requisitos, enlaces, direcciones, archivos = _contexto_form_tramite(
        request, tramite
    )
    direcciones_ok = not direcciones.is_bound or direcciones.is_valid()
    archivos_ok = not archivos.is_bound or archivos.is_valid()

    if form.is_valid():
        # Exigencias de la modalidad (Virtual/Mixta → enlaces oficiales,
        # Presencial/Mixta → direcciones). Antes de nada, porque el error
        # tiene que volver a la pantalla con el dato intacto.
        _validar_condiciones_de_modalidad(
            form, {'enlaces': enlaces, 'direcciones': direcciones}
        )

    requisitos_ok = requisitos.is_valid()
    enlaces_ok = enlaces.is_valid() and not form.errors
    if not (
        not form.errors
        and requisitos_ok
        and enlaces_ok
        and direcciones_ok
        and archivos_ok
    ):
        return False, form, requisitos, enlaces, direcciones, archivos

    tramite = form.save()
    # Los formsets apuntan al MISMO objeto: ya tiene pk al guardarlos.
    requisitos.instance = tramite
    _guardar_inlines(requisitos)
    enlaces.instance = tramite
    _guardar_inlines(enlaces)
    if direcciones.is_bound:
        direcciones.instance = tramite
        direcciones.save()
    if archivos.is_bound:
        archivos.instance = tramite
        _guardar_inlines(archivos)
    return True, form, requisitos, enlaces, direcciones, archivos


@solo_administrador
def panel_tramite_nuevo(request):
    """Alta de un trámite con sus requisitos, enlaces y direcciones."""
    if request.method == 'POST':
        guardado, form, requisitos, enlaces, direcciones, archivos = (
            _guardar_tramite(request, Tramite())
        )
        if guardado:
            messages.success(request, 'Trámite creado y publicado en el sitio.')
            return redirect('panel_tramites')
    else:
        form = TramitePanelForm()
        requisitos = RequisitoFormSet()
        enlaces = EnlaceFormSet()
        direcciones = DireccionFormSet()
        archivos = ArchivoFormSet()

    return render(request, 'panel/tramite_form.html', {
        'form': form,
        'requisitos': requisitos,
        'enlaces': enlaces,
        'direcciones': direcciones,
        'archivos': archivos,
        'tramite': None,
    })


@solo_administrador
def panel_tramite_editar(request, pk):
    """Edición del trámite: datos, requisitos, enlaces y direcciones."""
    tramite = get_object_or_404(
        Tramite.objects
        .select_related('tema', 'municipio', 'organismo')
        .prefetch_related('direcciones__municipio', 'archivos'),
        pk=pk,
    )
    if request.method == 'POST':
        guardado, form, requisitos, enlaces, direcciones, archivos = (
            _guardar_tramite(request, tramite)
        )
        if guardado:
            messages.success(request, 'Trámite guardado.')
            return redirect('panel_tramites')
    else:
        form, requisitos, enlaces, direcciones, archivos = (
            _contexto_form_tramite(request, tramite)
        )

    return render(request, 'panel/tramite_form.html', {
        'form': form,
        'requisitos': requisitos,
        'enlaces': enlaces,
        'direcciones': direcciones,
        'archivos': archivos,
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
            if not consulta.fecha_respuesta:
                consulta.fecha_respuesta = timezone.now()
                consulta.respondido_por = request.user
            consulta.save(update_fields=[
                'respuesta', 'estado', 'fecha_respuesta', 'respondido_por',
            ])
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


@solo_administrador
def panel_tickets(request):
    """Listado de tickets internos (y alta rápida para quien puede abrir).

    El administrativo ve los suyos; el administrador y el superusuario,
    todos. El filtro por estado es opcional.
    """
    if request.method == 'POST':
        if not usa_tickets(request.user):
            messages.error(
                request, 'Solo el rol administrativo puede abrir tickets.'
            )
            return redirect('panel_tickets')
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = _crear_ticket(request, form)
            messages.success(request, f'Ticket #{ticket.pk} guardado.')
            return redirect('panel_ticket_detalle', pk=ticket.pk)
    else:
        form = TicketForm() if usa_tickets(request.user) else None

    queryset = _tickets_visibles(request.user)
    estado = request.GET.get('estado', '')
    if estado in dict(Ticket.Estado.choices):
        queryset = queryset.filter(estado=estado)

    paginador = Paginator(queryset, POR_PAGINA)
    return render(request, 'panel/tickets_lista.html', {
        'pagina': paginador.get_page(request.GET.get('pagina')),
        'form_ticket': form,
        'estado': estado,
        'puede_gestionar': puede_gestionar_tickets(request.user),
    })


@solo_administrador
def panel_ticket_detalle(request, pk):
    """Detalle de un ticket: el dueño lo lee; el administrador y el
    superusuario además responden, cierran o reabren."""
    ticket = get_object_or_404(_tickets_visibles(request.user), pk=pk)
    gestiona = puede_gestionar_tickets(request.user)

    if request.method == 'POST':
        if not gestiona:
            messages.error(
                request,
                'Solo el administrador puede responder o cerrar tickets.'
            )
            return redirect('panel_ticket_detalle', pk=ticket.pk)

        accion = request.POST.get('accion', '')
        if accion == 'responder':
            form = RespuestaTicketForm(request.POST)
            if form.is_valid():
                ticket.respuesta = form.cleaned_data['respuesta'].strip()
                ticket.estado = Ticket.Estado.RESPONDIDO
                ticket.respondido_por = request.user
                ticket.fecha_respuesta = timezone.now()
                ticket.save(update_fields=[
                    'respuesta', 'estado', 'respondido_por',
                    'fecha_respuesta',
                ])
                messages.success(request, 'Respuesta guardada.')
                return redirect('panel_ticket_detalle', pk=ticket.pk)
        elif accion == 'cerrar':
            ticket.estado = Ticket.Estado.CERRADO
            ticket.save(update_fields=['estado'])
            messages.success(request, 'Ticket cerrado.')
            return redirect('panel_ticket_detalle', pk=ticket.pk)
        elif accion == 'reabrir':
            ticket.estado = Ticket.Estado.ABIERTO
            ticket.save(update_fields=['estado'])
            messages.success(request, 'Ticket reabierto.')
            return redirect('panel_ticket_detalle', pk=ticket.pk)
        else:
            messages.error(request, 'Acción no reconocida.')
    else:
        form = RespuestaTicketForm(initial={'respuesta': ticket.respuesta})

    return render(request, 'panel/ticket_detalle.html', {
        'ticket': ticket,
        'form': form,
        'puede_gestionar': gestiona,
    })


@solo_administrador
@require_POST
def panel_ticket_eliminar(request, pk):
    """Borra un ticket interno (el dueño o el superusuario)."""
    if not usa_tickets(request.user):
        messages.error(
            request, 'Los tickets internos son solo del rol administrativo.'
        )
        return redirect('panel')

    ticket = get_object_or_404(Ticket, pk=pk)
    if not (
        request.user.is_superuser or ticket.creado_por_id == request.user.pk
    ):
        messages.error(request, 'Solo podés eliminar tus propios tickets.')
        return redirect('panel_tickets')

    numero = ticket.pk
    ticket.delete()
    messages.success(request, f'Ticket #{numero} eliminado.')
    if request.POST.get('origen') == 'panel':
        return redirect('panel')
    return redirect('panel_tickets')


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
