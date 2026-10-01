"""Asistente virtual (chatbot con arquitectura RAG).

La logica del asistente NO vive aca: esta en `services/chatbot/`
(indexacion → recuperacion → generacion). Estas vistas solo:

  1. toman la pregunta del request,
  2. la pasan al pipeline,
  3. guardan la charla en la SESION (nunca en la base: RNF de privacidad)
     y la devuelven como pagina o como JSON.

El historial vive en `request.session['chatbot']` y se corta a los
ultimos 20 mensajes para no inflar la cookie.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from ..services.chatbot import es_limpieza, responder

# Maximo de mensajes que se guardan en la sesion
LIMITE_HISTORIAL = 20


def _agregar_mensaje(request, pregunta):
    """Pregunta al pipeline y guarda pregunta + respuesta en la sesion.

    Es el unico lugar que escribe en request.session['chatbot']: lo usan
    la pagina /chatbot/ y el modal (via /chatbot/api/). La charla anterior
    se le pasa al pipeline, que la usa para entender seguimientos («¿y el
    plazo?») y se la manda al modelo para que la respuesta siga el hilo.

    «limpiar» escrito a mano vacia la charla: es lo que promete la ayuda
    del asistente (el boton del chat manda accion=limpiar a la API).
    """
    historial = request.session.get('chatbot', [])
    if es_limpieza(pregunta):
        historial = []

    rta = responder(pregunta, historial)

    # Solo pk y titulo: minimiza el tamaño de la cookie de sesion
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
    request.session['chatbot'] = historial[-LIMITE_HISTORIAL:]
    return request.session['chatbot']


def _historial_para_json(request):
    """Igual que la sesión pero agregando la URL de cada tramite, para que
    el modal pueda pintar enlaces sin adivinar rutas en JavaScript."""
    salida = []
    for msg in request.session.get('chatbot', []):
        msg = dict(msg)
        if msg.get('tramites'):
            msg['tramites'] = [
                {**t, 'url': reverse('tramite_detalle', args=[t['pk']])}
                for t in msg['tramites']
            ]
        salida.append(msg)
    return salida


def chatbot(request):
    """Asistente. El POST pregunta al pipeline y guarda la charla en sesión.

    Es publico (cualquiera puede preguntar), pero la charla queda en la
    sesion de quien pregunta: no se almacena en Firebird.

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


@require_GET
def buscador_api(request):
    """JSON del asistente para la BARRA DE BUSQUEDA del sitio.

    GET ?q=… responde con el MISMO pipeline RAG que el chat, pero sin tocar
    la sesión: lo que se escribe en la barra de búsqueda no queda en la
    charla del modal (privacidad) ni la ensucia con búsquedas sueltas.

    Sin JavaScript no se usa este JSON: el <noscript> del listado lleva a
    /chatbot/?q=… que responde la misma pregunta en la página del chat.
    """
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'texto': '', 'tramites': []})

    rta = responder(q)
    return JsonResponse({
        'texto': rta['texto'],
        'tramites': [
            {'pk': t.pk, 'titulo': t.titulo,
             'url': reverse('tramite_detalle', args=[t.pk])}
            for t in rta['tramites']
        ],
    })


@login_required
@require_POST
def chatbot_limpiar(request):
    """Vacia la sesion de la charla."""
    request.session['chatbot'] = []
    return redirect('chatbot')
