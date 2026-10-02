"""Asistente virtual con arquitectura RAG (Retrieval Augmented Generation).

Pipeline de tres etapas:

    1. INDEXAR      services/chatbot/indexar.py
                    Convierte los tramites en fragmentos de texto
                    (ficha + requisitos) con su fuente.
    2. RECUPERAR    services/chatbot/recuperacion.py
                    Normaliza la pregunta, la expande con sinonimos y
                    puntua cada fragmento con BM25. Si nada supera el
                    umbral, no hay contexto util.
    3. GENERAR      services/chatbot/generacion.py
                    Arma la respuesta con el contexto recuperado: una
                    plantilla anclada a los fragmentos, con variantes
                    para no repetirse. Nunca inventa: si el umbral no se
                    alcanza, dice que no dispone de esa informacion, y
                    una pregunta por monto que no esta indexada se
                    contesta con «no dispongo» antes de redactar.

Criterios del documento que garantiza este diseno:

    · Precisión contextual ..... solo se responde con fragmentos indexados
    · Manejo de alucinaciones .. umbral + «no dispongo de esa información»
                                 + el corte de montos de generacion.py
    · Cita de fuentes .......... cada respuesta enlaza sus tramites
    · Privacidad ............... la charla vive en la sesion, no en la base

Uso tipico (desde una vista):

    from munitramites.services.chatbot import es_limpieza, responder
    historial = request.session.get('chatbot', [])
    if es_limpieza(pregunta):        # «limpiar» escrito a mano
        historial = []
    rta = responder(pregunta, historial)
    rta['texto']      # str legible
    rta['tramites']   # [Tramite, …] fuentes citadas

Con `historial` el asistente entiende seguimientos («¿y el plazo?»): si la
pregunta es corta, se busca junto con la pregunta anterior del usuario
para saber de qué habla.
"""

from .pipeline import es_limpieza, responder

__all__ = ['es_limpieza', 'responder']
