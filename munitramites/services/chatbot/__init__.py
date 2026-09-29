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
                    Arma la respuesta con el contexto recuperado. Si hay
                    una API key configurada (settings.CHATBOT_LLM), la
                    respuesta la genera el LLM; si no, una plantilla
                    anclada a los fragmentos. Nunca inventa: si el umbral
                    no se alcanza, dice que no dispone de esa informacion.

Criterios del documento que garantiza este diseno:

    · Precisión contextual ..... solo se responde con fragmentos indexados
    · Manejo de alucinaciones .. umbral + «no dispongo de esa información»
    · Cita de fuentes .......... cada respuesta enlaza sus tramites
    · Privacidad ............... la charla vive en la sesion, no en la base

Uso tipico (desde una vista):

    from munitramites.services.chatbot import responder
    rta = responder('¿qué necesito para renovar el DNI?')
    rta['texto']      # str legible
    rta['tramites']   # [Tramite, …] fuentes citadas
"""

from .pipeline import responder

__all__ = ['responder']
