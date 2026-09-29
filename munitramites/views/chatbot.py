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
from django.views.decorators.http import require_POST

from ..services.chatbot import responder

# Maximo de mensajes que se guardan en la sesion
LIMITE_HISTORIAL = 20


def _agregar_mensaje(request, pregunta):
    """Pregunta al pipeline y guarda pregunta + respuesta en la sesion.

    Es el unico lugar que escribe en request.session['chatbot']: lo usan
    la pagina /chatbot/ y el modal (via /chatbot/api/).
    """
    historial = request.session.get('chatbot', [])
    rta = responder(pregunta)

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


@login_required
@require_POST
def chatbot_limpiar(request):
    """Vacia la sesion de la charla."""
    request.session['chatbot'] = []
    return redirect('chatbot')
