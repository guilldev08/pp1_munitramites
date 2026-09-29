"""
Vistas. >>> ACÁ VIVE LA LOGICA <<<

Cada vista hace 3 cosas y nada mas:

    1. Recibe el request
    2. Consulta / guarda datos en Firebird (via models)
    3. Devuelve un template con esos datos

Si una vista necesita tocar la base, se agrega ACA y su URL en urls.py.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ConsultaForm, RegistroForm, SoporteForm, TramiteFiltroForm
from .models import Consulta, Municipio, Organismo, Requisito, Tramite

# Las consultas que llegan desde /soporte/ se guardan con este prefijo en el
# asunto: asi el admin y «Mis consultas» las distinguen sin una columna nueva.
PREFIJO_SOPORTE = 'Soporte: '


# --------------------------------------------------------------------------
# Listado de tramites (compartido por la portada y /tramites/)
# --------------------------------------------------------------------------
def _contexto_lista_tramites(request):
    """Filtros + paginacion de la lista de tramites.

    El form de filtros y los links del paginador son RELATIVOS, asi el mismo
    bloque anda igual en la portada (/) que en /tramites/.
    """
    filtros = TramiteFiltroForm(request.GET or None)
    queryset = (
        Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo')
        .prefetch_related('requisitos')
    )
    queryset = filtros.filtrar(queryset)

    paginador = Paginator(queryset, 6)
    pagina = paginador.get_page(request.GET.get('pagina'))

    # Querystring sin el parametro 'pagina', para los links del paginador
    params = request.GET.copy()
    params.pop('pagina', None)

    return {
        'pagina': pagina,
        'filtros': filtros,
        'qs': params.urlencode(),
        'hay_filtros': any(
            request.GET.get(k) for k in ('q', 'tema', 'municipio', 'modalidad')
        ),
    }


# --------------------------------------------------------------------------
# Paginas publicas
# --------------------------------------------------------------------------
def inicio(request):
    """Portada: hero con la barra del chatbot + lista de tramites con filtros."""
    context = {
        'total_tramites': Tramite.objects.filter(activo=True).count(),
        'total_organismos': Organismo.objects.count(),
        'total_municipios': Municipio.objects.count(),
        'total_requisitos': Requisito.objects.count(),
        'temas': (
            Tramite.objects.filter(activo=True)
            .values('tema')
            .annotate(total=Count('id'))
            .order_by('tema')
        ),
    }
    context.update(_contexto_lista_tramites(request))
    return render(request, 'inicio.html', context)


def tramites(request):
    """Listado con filtros por texto, tema, municipio y modalidad."""
    return render(
        request, 'tramites/lista.html', _contexto_lista_tramites(request)
    )


def tramite_detalle(request, pk):
    """Ficha completa: organismo, requisitos y enlaces oficiales."""
    tramite = get_object_or_404(
        Tramite.objects.select_related('municipio', 'organismo')
        .prefetch_related('requisitos'),
        pk=pk, activo=True,
    )
    relacionados = (
        Tramite.objects.filter(
            activo=True, tema=tramite.tema
        ).exclude(pk=tramite.pk)[:3]
    )
    return render(request, 'tramites/detalle.html', {
        'tramite': tramite,
        'relacionados': relacionados,
    })


# --------------------------------------------------------------------------
# Chatbot (consulta real contra Firebird)
# --------------------------------------------------------------------------
def _responder_chatbot(pregunta):
    """Busca en la base y devuelve {texto, tramites}. Sin API externa.

    Devuelve tramites como objetos aparte para que el template pueda
    pintar enlaces reales, no texto plano.
    """
    pregunta = pregunta.strip()
    if not pregunta:
        return {
            'texto': 'Escribí una consulta, por ejemplo: «¿cómo renuevo el DNI?».',
            'tramites': [],
        }

    bajo = pregunta.lower()

    # Saludo
    if any(p in bajo for p in ('hola', 'buenos dias', 'buenas')):
        return {
            'texto': ('¡Hola! Soy el asistente de trámites de Misiones. '
                      'Preguntame por un trámite, por ejemplo: «licencia de '
                      'conducir» o «partida de nacimiento».'),
            'tramites': [],
        }

    # Ayuda
    if bajo in ('ayuda', 'help'):
        return {
            'texto': ('Puedo buscar trámites por nombre, tema o requisito. '
                      'Probá con «antecedentes penales», «comercio» o «salud».'),
            'tramites': [],
        }

    base = Tramite.objects.filter(activo=True).select_related(
        'organismo', 'municipio'
    ).prefetch_related('requisitos')

    def buscar(termino):
        return base.filter(
            Q(titulo__icontains=termino)
            | Q(descripcion__icontains=termino)
            | Q(tema__icontains=termino)
            | Q(requisitos__descripcion__icontains=termino)
        ).distinct()[:4]

    coincidencias = buscar(pregunta)

    # Si no hubo suerte, reintenta con la palabra mas significativa
    if not coincidencias:
        palabras = [p for p in pregunta.split() if len(p) > 3]
        if palabras:
            coincidencias = buscar(palabras[0])

    if not coincidencias:
        return {
            'texto': (f'No encontré trámites para «{pregunta}». Probá con '
                      f'otro término o escribí «ayuda».'),
            'tramites': [],
        }

    n = len(coincidencias)
    texto = (
        f'Encontré {n} trámite{"s" if n != 1 else ""}: '
        f'abrí la ficha para ver todos los requisitos.'
    )
    return {'texto': texto, 'tramites': list(coincidencias)}


def _agregar_mensaje(request, pregunta):
    """Guarda la pregunta + respuesta en la sesion y devuelve la charla.

    Es el unico lugar que escribe en request.session['chatbot']: lo usan
    la pagina /chatbot/ y el modal (via /chatbot/api/).
    """
    historial = request.session.get('chatbot', [])
    rta = _responder_chatbot(pregunta)

    # Solo pk y titulo: minimiza el tamaño de la cookie de sesión
    historial = historial + [
        {'rol': 'usuario', 'texto': pregunta},
        {
            'rol': 'bot',
            'texto': rta['texto'],
            'tramites': [
                {'pk': t.pk, 'titulo': t.titulo}
                for t in rta['tramites']
            ],
        },
    ]
    # Corta la charla para no inflar la cookie de sesión
    request.session['chatbot'] = historial[-20:]
    return request.session['chatbot']


def _historial_para_json(request):
    """Igual que la sesion pero agregando la URL de cada tramite, para que
    el modal pueda pintar enlaces sin adivinar rutas en JavaScript."""
    salida = []
    for msg in request.session.get('chatbot', []):
        msg = dict(msg)
        if msg.get('tramites'):
            msg['tramites'] = [
                {
                    **t,
                    'url': reverse('tramite_detalle', args=[t['pk']]),
                }
                for t in msg['tramites']
            ]
        salida.append(msg)
    return salida


def chatbot(request):
    """Asistente. El POST consulta Firebird y guarda la charla en sesión.

    Es publico (cualquiera puede preguntar), pero si el usuario esta
    logueado guardamos la charla en su sesion.

    Acepta GET ?q=… como alternativa sin JavaScript: la pregunta se responde
    aca mismo y se muestra en la pagina.
    """
    historial = request.session.get('chatbot', [])

    if request.method == 'POST':
        historial = _agregar_mensaje(request, request.POST.get('mensaje', ''))
    elif request.GET.get('q', '').strip():
        historial = _agregar_mensaje(request, request.GET['q'])

    return render(request, 'chatbot.html', {'historial': historial})


def chatbot_api(request):
    """JSON del chatbot: lo usa la pestaña emergente del chat.

    GET  → devuelve la charla guardada en la sesión
    POST → agrega un mensaje (o `accion=limpiar` para vaciarla)
    """
    if request.method == 'POST':
        if request.POST.get('accion') == 'limpiar':
            request.session['chatbot'] = []
        else:
            _agregar_mensaje(request, request.POST.get('mensaje', ''))

    return JsonResponse({'historial': _historial_para_json(request)})


@login_required
@require_POST
def chatbot_limpiar(request):
    """Vacia la sesion de la charla."""
    request.session['chatbot'] = []
    return redirect('chatbot')


# --------------------------------------------------------------------------
# Consultas
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Soporte (solo con cuenta logueada)
# --------------------------------------------------------------------------
@login_required
def soporte(request):
    """Pagina de soporte: formulario + historial de pedidos del usuario.

    Lo que llega se guarda como una Consulta con el asunto empezando por
    «Soporte: », asi aparece en el admin y en «Mis consultas» y puede
    responderse con el mismo flujo que una consulta normal.
    """
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


# --------------------------------------------------------------------------
# Registro de ciudadanos
# --------------------------------------------------------------------------
def registro(request):
    """Alta de usuario con el sistema de usuarios de Django."""
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
    # si el POST vino con errores, manda el form validoado para que se vean.
    return render(request, 'registro.html', {
        'form': form,
        'form_registro': form,
    })


# --------------------------------------------------------------------------
# API minima (para futuro, no requiere JS)
# --------------------------------------------------------------------------
def api_tramites(request):
    """Listado liviano de tramites. Útil para integraciones."""
    datos = [
        {
            'id': t.pk,
            'titulo': t.titulo,
            'tema': t.tema,
            'modalidad': t.modalidad,
            'municipio': t.municipio.nombre,
            'organismo': t.organismo.nombre,
        }
        for t in Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo')
    ]
    return JsonResponse({'count': len(datos), 'tramites': datos})
