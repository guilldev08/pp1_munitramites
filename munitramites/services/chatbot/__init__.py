"""Asistente virtual con arquitectura RAG (Retrieval Augmented Generation).

Pipeline de tres etapas:

    1. INDEXAR      services/chatbot/indexar.py
                    Convierte los tramites en fragmentos de texto
                    (ficha + requisitos) con su fuente. Se invalida solo
                    al editar un tramite (senales).

    2. RECUPERAR    services/chatbot/recuperacion.py
                    Normaliza la pregunta, la expande con sinonimos y
                    puntua cada fragmento con BM25. Si nada supera el
                    umbral, no hay contexto util.

    3. GENERAR      services/chatbot/generacion.py
                    Redacta la respuesta. Con CHATBOT_LLM='groq' la
                    redaccion es del modelo de Groq con el contexto en
                    la mano (services/chatbot/llm/, contra la API de
                    Groq); sin clave, sin modelo —o si se cae— vuelve a
                    la plantilla local, anclada a los
                    fragmentos y con variantes para no repetirse. Nunca
                    inventa: los datos de tramites salen solo del
                    contexto, y una pregunta por monto que no esta
                    indexada se contesta con «no dispongo».

    ORQUESTAR      services/chatbot/pipeline.py
                    saludos/ordenes fijas (rápidas), seguimientos
                    cortos, umbral y entrega final: texto + tramites
                    fuente. Sin fragmentos, con modelo, explica el
                    portal o redirige si el tema es ajeno; sin modelo,
                    el «no encontré» clásico.

Criterios del documento que garantiza este diseno:

    · Precisión contextual ..... solo se responde con fragmentos indexados
    · Manejo de alucinaciones .. umbral + «no dispongo de esa información»
                                 + el corte de montos de generacion.py
    · Cita de fuentes .......... cada respuesta enlaza sus tramites
    · Privacidad ............... cada usuario tiene su propio historial

Uso tipico (desde una vista):

    from munitramites.services.chatbot import es_limpieza, responder
    historial = [...]                # últimos mensajes de la conversación
    if es_limpieza(pregunta):        # «limpiar» escrito a mano
        historial = []
    rta = responder(pregunta, historial)
    rta['texto']      # str legible
    rta['tramites']   # [Tramite, …] fuentes citadas

El historial persistente (ConversacionChat/MensajeChat) lo maneja la
vista; este paquete solo recibe la lista de mensajes previos.

Con `historial` el asistente entiende seguimientos («¿y el plazo?»): si la
pregunta es corta, se busca junto con la pregunta anterior del usuario
para saber de qué habla.

Tests: munitramites/tests/test_chatbot.py (pipeline y plantilla),
test_llm.py (contrato con el modelo, siempre simulado).
"""

from .pipeline import es_limpieza, responder

__all__ = ['es_limpieza', 'responder']
