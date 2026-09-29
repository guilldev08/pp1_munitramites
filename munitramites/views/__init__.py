"""Vistas del sitio, agrupadas por modulo.

    pagina.py     portada (hero + chat + lista de tramites)
    tramites.py   listado con filtros y ficha
    chatbot.py    asistente (pagina, JSON y limpiar)
    consultas.py  consultas y sugerencias de los ciudadanos
    soporte.py    pedidos de soporte
    cuenta.py     registro y perfil del ciudadano
    api.py        JSON liviano para integraciones

`urls.py` hace `from . import views` y aca se re-exportan todas
las vistas, asi las rutas quedan iguales (`views.inicio`, `views.tramites`…)
y cada modulo se puede tocar por separado.

Para AGREGAR UNA VISTA NUEVA:
  1. creá o elegí un modulo dentro de `views/`,
  2. exportala aca,
  3. agregá su `path(...)` en `urls.py`.
"""

from .api import api_tramites
from .chatbot import chatbot, chatbot_api, chatbot_limpiar
from .consultas import consulta_detalle, consulta_nueva, consultas
from .cuenta import perfil, registro
from .pagina import inicio
from .soporte import PREFIJO_SOPORTE, soporte
from .tramites import tramite_detalle, tramites

__all__ = [
    'PREFIJO_SOPORTE',
    'api_tramites',
    'chatbot',
    'chatbot_api',
    'chatbot_limpiar',
    'consulta_detalle',
    'consulta_nueva',
    'consultas',
    'inicio',
    'perfil',
    'registro',
    'soporte',
    'tramite_detalle',
    'tramites',
]
