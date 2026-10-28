"""Asistente virtual (chatbot con arquitectura RAG).

La lógica del asistente NO vive acá: está en `services/chatbot/`
(indexación → recuperación → generación). Estas vistas solo:

  1. toman la pregunta del request,
  2. la pasan al pipeline,
  3. guardan la conversación en Firebird y la devuelven como JSON.

Cada usuario tiene sus propias conversaciones (`ConversacionChat`), con
sus mensajes (`MensajeChat`) y las fichas citadas (`FuenteMensaje`). El
historial ya no vive en la cookie de sesión: así se puede retomar una
charla desde otro navegador y entrar a conversaciones distintas.

Las respuestas del modelo NO traen enlaces: el sistema enlaza dentro del
texto el título de cada trámite citado con su ficha interna. Eso evita
que el modelo invente URLs o recomendaciones externas.
"""

import re
import unicodedata

from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from ..models import (
    ConversacionChat,
    FuenteMensaje,
    MensajeChat,
)
from ..services.chatbot import es_limpieza, responder

TITULO_NUEVO = 'Nueva conversación'

# Mensajes que se le pasan al pipeline para entender seguimientos. El
# historial completo queda guardado; esto solo limita el contexto.
LIMITE_CONTEXTO = 20

# Palabras que no alcanzan para identificar un trámite cuando el modelo
# no escribió el título completo. Se comparan sin tildes y en minúsculas.
_PALABRAS_SIN_PESO = {
    'a', 'al', 'algo', 'como', 'con', 'de', 'del', 'el', 'en', 'la',
    'las', 'los', 'o', 'para', 'por', 'que', 'sin', 'su', 'sus', 'un',
    'una', 'unas', 'unos', 'y', 'tramite', 'tramites', 'solicitud',
    'obtencion', 'renovacion', 'inscripcion', 'registro',
    # Palabras que aparecen en muchos títulos y no identifican una ficha
    # («a los 14 años», «nuevo ejemplar»): enlazarlas confunde.
    'ano', 'anos', 'actualizacion', 'alta', 'baja', 'cambio', 'ejemplar',
    'mayores', 'menores', 'modificacion', 'nuevo', 'nueva', 'servicio',
}


def _titulo_desde(pregunta):
    """Título corto y legible a partir de la primera pregunta."""
    texto = ' '.join((pregunta or '').split())
    if not texto:
        return TITULO_NUEVO
    if len(texto) <= 60:
        return texto
    return texto[:59].rstrip() + '…'


def _crear_conversacion(request):
    """Crea una charla nueva, la activa y limpia las anteriores vacías.

    Dejar el id en la sesión es lo que hace que el mensaje siguiente se
    guarde en la conversación recién creada y no en la que estaba activa.
    """
    ConversacionChat.objects.filter(
        usuario=request.user, mensajes__isnull=True
    ).delete()
    conversacion = ConversacionChat.objects.create(usuario=request.user)
    request.session['chat_conversacion_id'] = conversacion.pk
    return conversacion


def _conversacion_autorizada(user, pk):
    """La conversación `pk` si pertenece al usuario; si no, None."""
    if not pk:
        return None
    try:
        return ConversacionChat.objects.get(pk=pk, usuario=user)
    except (ConversacionChat.DoesNotExist, TypeError, ValueError):
        return None


def _conversacion_para_leer(request):
    """La conversación pedida, la de la sesión o la última del usuario."""
    if not request.user.is_authenticated:
        return None

    pk = (
        request.POST.get('conversacion')
        or request.GET.get('c')
        or request.GET.get('conversacion')
        or request.session.get('chat_conversacion_id')
    )
    conversacion = _conversacion_autorizada(request.user, pk)
    if conversacion is None:
        conversacion = (
            ConversacionChat.objects
            .filter(usuario=request.user)
            .order_by('-actualizado', '-id')
            .first()
        )
    if conversacion is not None:
        request.session['chat_conversacion_id'] = conversacion.pk
    return conversacion


def _conversacion_para_escribir(request):
    """La conversación indicada por POST o sesión; si no hay, crea una."""
    pk = (
        request.POST.get('conversacion')
        or request.session.get('chat_conversacion_id')
    )
    conversacion = _conversacion_autorizada(request.user, pk)
    if conversacion is None:
        conversacion = _crear_conversacion(request)
    request.session['chat_conversacion_id'] = conversacion.pk
    return conversacion


def _historial_para_pipeline(conversacion):
    """Los últimos mensajes, con el formato que espera `responder`."""
    mensajes = list(conversacion.mensajes.all())[-LIMITE_CONTEXTO:]
    return [
        {'rol': mensaje.rol, 'texto': mensaje.texto}
        for mensaje in mensajes
    ]


def _agregar_mensaje(pregunta, conversacion):
    """Pregunta al pipeline y persiste la pregunta, la respuesta y fuentes."""
    pregunta = (pregunta or '').strip()
    if not pregunta:
        return conversacion

    limpieza = es_limpieza(pregunta)
    if limpieza:
        conversacion.mensajes.all().delete()

    historial = _historial_para_pipeline(conversacion)
    respuesta = responder(pregunta, historial)

    MensajeChat.objects.create(
        conversacion=conversacion,
        rol=MensajeChat.Rol.USUARIO,
        texto=pregunta,
    )
    mensaje_bot = MensajeChat.objects.create(
        conversacion=conversacion,
        rol=MensajeChat.Rol.BOT,
        texto=respuesta['texto'],
    )
    FuenteMensaje.objects.bulk_create([
        FuenteMensaje(
            mensaje=mensaje_bot,
            tramite=tramite,
            titulo=tramite.titulo,
            orden=orden,
        )
        for orden, tramite in enumerate(respuesta['tramites'], 1)
    ])

    if conversacion.titulo == TITULO_NUEVO and not limpieza:
        conversacion.titulo = _titulo_desde(pregunta)
    conversacion.save()
    return conversacion


def _normalizar(texto):
    """Minúsculas y sin tildes, conservando un carácter por original.

    Así «Renovación» del texto y «Renovacion» del título se comparan
    igual, sin correr los índices que después se usan para cortar el
    texto original.
    """
    salida = []
    for caracter in texto or '':
        base = unicodedata.normalize('NFKD', caracter)
        base = ''.join(c for c in base if not unicodedata.combining(c))
        salida.append((base[:1] or caracter).lower())
    return ''.join(salida)


def _candidatos(titulo):
    """El título completo y, como respaldo, sus palabras significativas."""
    titulo = (titulo or '').strip()
    if not titulo:
        return []

    candidatos = [_normalizar(titulo)]
    palabras = []
    for palabra in re.findall(r'[^\W_]+', titulo, re.UNICODE):
        normal = _normalizar(palabra)
        if len(normal) >= 3 and normal not in _PALABRAS_SIN_PESO:
            palabras.append(normal)

    # Las palabras más largas primero: «renovacion» antes que «dni», pero
    # «dni» sigue estando si el texto no dice «renovacion».
    palabras.sort(key=len, reverse=True)
    for palabra in palabras:
        if palabra not in candidatos:
            candidatos.append(palabra)
    return candidatos


def _buscar_en_texto(texto_normalizado, candidatos, ocupados):
    """Primera aparición libre de algún candidato, con límites de palabra."""
    for candidato in candidatos:
        if not candidato:
            continue
        patron = re.compile(
            r'(?<!\w)' + re.escape(candidato) + r'(?!\w)'
        )
        for encontrado in patron.finditer(texto_normalizado):
            inicio, fin = encontrado.start(), encontrado.end()
            if any(
                inicio < ocupado_fin and ocupado_inicio < fin
                for ocupado_inicio, ocupado_fin in ocupados
            ):
                continue
            return inicio, fin
    return None


def _segmentos_con_enlaces(texto, tramites):
    """Parte el texto en segmentos y enlaza los trámites citados.

    `tramites` son dicts con `titulo` y `url`. Se enlaza la primera
    aparición de cada título (o de su palabra más significativa si el
    modelo no lo escribió completo) y el resto queda como texto plano.
    El modelo nunca arma estas URLs: salen de `reverse('tramite_detalle')`.
    """
    texto = texto or ''
    if not texto or not tramites:
        return [{'texto': texto, 'url': ''}]

    normalizado = _normalizar(texto)

    # Los títulos más largos primero: si hay «DNI» y «Renovacion de DNI»,
    # el segundo tiene que quedarse con la frase completa.
    ordenados = sorted(
        tramites,
        key=lambda t: len(t.get('titulo') or ''),
        reverse=True,
    )

    candidatos = []
    for indice, tramite in enumerate(ordenados):
        titulo = (tramite.get('titulo') or '').strip()
        url = tramite.get('url') or ''
        if not titulo or not url:
            continue
        candidatos.append((indice, url, _candidatos(titulo)))

    enlaces = []
    ocupados = []
    enlazados = set()

    # Primero los títulos completos, de más largo a más corto. Si dos
    # fichas comparten una palabra («DNI Exprés» y «Pasaporte Exprés»),
    # así gana la que aparece entera en el texto y no queda partida.
    for indice, url, opciones in candidatos:
        encontrado = _buscar_en_texto(
            normalizado, opciones[:1], ocupados,
        )
        if encontrado is None:
            continue
        inicio, fin = encontrado
        enlaces.append((inicio, fin, url))
        ocupados.append((inicio, fin))
        enlazados.add(indice)

    # Recién después, la palabra significativa de las fichas que no
    # aparecieron con el título completo.
    for indice, url, opciones in candidatos:
        if indice in enlazados:
            continue
        encontrado = _buscar_en_texto(
            normalizado, opciones[1:], ocupados,
        )
        if encontrado is None:
            continue
        inicio, fin = encontrado
        enlaces.append((inicio, fin, url))
        ocupados.append((inicio, fin))

    if not enlaces:
        return [{'texto': texto, 'url': ''}]

    enlaces.sort(key=lambda enlace: enlace[0])
    segmentos = []
    posicion = 0
    for inicio, fin, url in enlaces:
        if inicio > posicion:
            segmentos.append({
                'texto': texto[posicion:inicio],
                'url': '',
            })
        segmentos.append({'texto': texto[inicio:fin], 'url': url})
        posicion = fin
    if posicion < len(texto):
        segmentos.append({'texto': texto[posicion:], 'url': ''})
    return segmentos


def _serializar_mensaje(mensaje):
    fuentes = [
        {
            'pk': fuente.tramite_id,
            'titulo': fuente.titulo,
            'url': (
                reverse('tramite_detalle', args=[fuente.tramite_id])
                if fuente.tramite_id else ''
            ),
        }
        for fuente in mensaje.fuentes.all()
    ]
    return {
        'rol': mensaje.rol,
        'texto': mensaje.texto,
        'tramites': fuentes,
        'segmentos': _segmentos_con_enlaces(mensaje.texto, fuentes),
    }


def _serializar_historial(conversacion):
    if conversacion is None:
        return []
    mensajes = conversacion.mensajes.prefetch_related('fuentes').all()
    return [_serializar_mensaje(mensaje) for mensaje in mensajes]


def _serializar_conversacion(conversacion):
    if conversacion is None:
        return None
    return {
        'id': conversacion.pk,
        'titulo': conversacion.titulo,
        'actualizado': conversacion.actualizado.isoformat(),
    }


def _lista_conversaciones(user):
    """Todas las conversaciones del usuario, de la más nueva a la más vieja."""
    return [
        _serializar_conversacion(conversacion)
        for conversacion in (
            ConversacionChat.objects
            .filter(usuario=user)
            .order_by('-actualizado', '-id')
        )
    ]


def _respuesta_json(request, conversacion):
    return JsonResponse({
        'conversacion': _serializar_conversacion(conversacion),
        'conversaciones': _lista_conversaciones(request.user),
        'historial': _serializar_historial(conversacion),
    })


def chatbot_api(request):
    """JSON del chatbot: lo usa la pestaña emergente del chat.

    GET  → conversación activa, lista completa de conversaciones e historial.
    POST → agrega un mensaje o ejecuta `nueva` o `seleccionar`.

    Sin sesión el POST contesta 403 (y no un redirect, que el fetch
    seguiría hasta devolver HTML): el JavaScript del modal aprovecha ese
    403 para abrir el de login en lugar de pintar un error.
    """
    if not request.user.is_authenticated:
        if request.method == 'POST':
            return JsonResponse(
                {'error': 'Iniciá sesión para usar el asistente.'},
                status=403,
            )
        return JsonResponse({
            'conversacion': None,
            'conversaciones': [],
            'historial': [],
        })

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'nueva':
            conversacion = _crear_conversacion(request)
        elif accion == 'seleccionar':
            conversacion = _conversacion_autorizada(
                request.user,
                request.POST.get('conversacion') or request.POST.get('id'),
            )
            if conversacion is None:
                return JsonResponse(
                    {'error': 'Esa conversación no existe.'},
                    status=404,
                )
            request.session['chat_conversacion_id'] = conversacion.pk
        else:
            mensaje = (request.POST.get('mensaje') or '').strip()
            if not mensaje:
                return JsonResponse(
                    {'error': 'Escribí una consulta.'},
                    status=400,
                )
            conversacion = _conversacion_para_escribir(request)
            _agregar_mensaje(mensaje, conversacion)

        return _respuesta_json(request, conversacion)

    conversacion = _conversacion_para_leer(request)
    return _respuesta_json(request, conversacion)


@require_GET
def buscador_api(request):
    """JSON del asistente para la BARRA DE BUSQUEDA del sitio.

    GET ?q=… responde con el MISMO pipeline RAG que el chat, pero sin tocar
    ninguna conversación: lo que se escribe en la barra de búsqueda no queda
    en el historial (privacidad) ni lo ensucia con búsquedas sueltas.

    El modelo SOLO redacta con sesión iniciada: una visita anónima
    recibe la respuesta de las plantillas. Así la barra pública no
    gasta la API de Groq; el chat (con sesión) sí usa el modelo para
    redactar con naturalidad, siempre dentro de los trámites.

    La barra funciona con JavaScript; el modal del asistente es la
    única entrada al chat.
    """
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'texto': '', 'tramites': [], 'segmentos': []})

    rta = responder(q, usar_llm=request.user.is_authenticated)
    tramites = [
        {'pk': t.pk, 'titulo': t.titulo,
         'url': reverse('tramite_detalle', args=[t.pk])}
        for t in rta['tramites']
    ]
    return JsonResponse({
        'texto': rta['texto'],
        'tramites': tramites,
        'segmentos': _segmentos_con_enlaces(rta['texto'], tramites),
    })
