"""Atajos de querystring para los listados del panel.

Se cargan con `{% load panel_tags %}` y sirven para que los links de
filtro, de orden y de paginación conserven todos los demás parámetros
de la URL actual (igual que los filtros del /admin/ de Django).
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def qs(context, **cambios):
    """La querystring actual con los parámetros dados pisados.

    * `{% qs tema=t.pk %}` agrega o cambia un parámetro,
    * `{% qs estado=None %}` lo borra,
    * siempre se pierde `pagina`, porque filtrar u ordenar reinicia la
      paginación.
    """
    params = context['request'].GET.copy()
    params.pop('pagina', None)
    for clave, valor in cambios.items():
        if valor is None:
            params.pop(clave, None)
        else:
            params[clave] = str(valor)
    return f'?{params.urlencode()}'
