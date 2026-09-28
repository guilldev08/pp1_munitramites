"""
Filtros de template. >>> ACÁ SE AGREGAN FILTROS <<<

Uso en un template:

    {% load hora %}
    {{ objeto.fecha|hora_local|date:"d/m/Y H:i" }}
"""

from datetime import timezone as dt_timezone

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def hora_local(value):
    """Pasa un datetime a la hora local del proyecto.

    ¿Por qué hace falta? Firebird guarda TIMESTAMP sin zona horaria, asi
    que el driver devuelve un datetime "naive". Con USE_TZ=True Django
    guarda en UTC, de modo que el valor que llega aca es UTC naive y el
    filtro |date lo mostraria tal cual (3 horas corridas en Argentina).

    Este filtro lo interpreta como UTC y lo convierte a TIME_ZONE.
    """
    if not value or not hasattr(value, 'tzinfo'):
        return value

    if timezone.is_naive(value):
        # El driver no devolvio zona: asumimos UTC (como guardo Django)
        value = timezone.make_aware(value, dt_timezone.utc)

    return timezone.localtime(value)
