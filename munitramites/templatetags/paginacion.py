"""Etiqueta `paginas_ventana`: paginador con ventana deslizante.

`{{ pagina.paginator.page_range }}` tira TODOS los números de página. En un
listado largo (23 páginas, p. ej.) la barra se desborda y queda en dos filas
medio rotas.

Esta etiqueta devuelve en cambio una ventana de ~5 números centrada en la
página actual: a medida que se avanza, los de atrás se corren y desaparecen
de a uno, y al final siempre queda `… <última>`.

    {% for n in pagina|paginas_ventana %}
        {% if n == '…' %}        {# centinela: no es un enlace #}
        {% elif n == pagina.number %}
        {% else %}               {# número enlaceable #}

Si quedan uno o dos números sueltos antes de la última página, la ventana se
alarga y los muestra en vez de gastar un `…`. Si el listado es corto (hasta
`ancho + 3` páginas) entran todos los números y no hay nada que saltear.
"""

from django import template

register = template.Library()

# Centinela: en la plantilla se compara contra `'…'`
ELIPSIS = '…'

# Números de página visibles en la ventana
ANCHO = 5


@register.filter
def paginas_ventana(pagina, ancho=ANCHO):
    """Lista de números de página para el paginador, con `…` de relleno.

    Devuelve enteros (páginas) y el string `'…'` como centinela, listos para
    recorrer con `{% for %}`.
    """
    try:
        total = int(pagina.paginator.num_pages)
        actual = int(pagina.number)
    except (AttributeError, TypeError, ValueError):
        return []

    ancho = max(3, int(ancho))

    # Pocas páginas: entran todas y no hace falta saltear nada.
    if total <= ancho + 3:
        return list(range(1, total + 1))

    # Ventana centrada en la página actual, sin pasarse del final.
    mitad = ancho // 2
    inicio = max(1, min(actual - mitad, total - ancho + 1))
    fin = inicio + ancho - 1

    # Si antes de la última quedan uno o dos números, se muestran todos:
    # un `…` que esconde una sola página queda peor que la página entera.
    if total - fin <= 2:
        fin = total

    paginas = list(range(inicio, fin + 1))
    if fin < total:
        paginas.extend([ELIPSIS, total])
    return paginas
