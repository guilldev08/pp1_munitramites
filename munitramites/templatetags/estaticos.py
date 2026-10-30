"""Etiqueta `estatico`: como `{% static %}`, pero con `?v=<mtime>`.

Django solo manda `Last-Modified` en desarrollo (sin `Cache-Control`), y
el navegador puede quedarse con la copia vieja de un CSS o un JS aunque
el archivo haya cambiado. La fecha de modificación en la URL hace que lo
vuelva a pedir cuando el archivo cambia, sin tocar nada a mano.
"""

import os

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


@register.simple_tag
def estatico(ruta):
    """URL del estático con la fecha de modificación, ej.: `…/app.js?v=…`."""
    url = staticfiles_storage.url(ruta)
    absoluto = finders.find(ruta)
    if not absoluto:
        return url
    try:
        modificado = os.path.getmtime(absoluto)
    except OSError:
        return url
    return f'{url}?v={int(modificado)}'