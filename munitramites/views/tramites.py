"""Vistas de tramites: listado con filtros y ficha.

El listado se comparte entre la portada (`/`) y `/tramites/`, por eso el
helper de contexto vive aca y `views/pagina.py` lo importa.
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from ..forms import TramiteFiltroForm
from ..models import Tramite

# Tramites por pagina del listado
POR_PAGINA = 6


def contexto_lista_tramites(request):
    """Filtros + paginacion de la lista de tramites.

    El form de filtros y los links del paginador son RELATIVOS, asi el mismo
    bloque anda igual en la portada (/) que en /tramites/.
    """
    filtros = TramiteFiltroForm(request.GET or None)
    queryset = (
        Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo', 'tema')
        .prefetch_related('requisitos')
    )
    queryset = filtros.filtrar(queryset)

    paginador = Paginator(queryset, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('pagina'))

    # Querystring sin el parametro 'pagina', para los links del paginador
    params = request.GET.copy()
    params.pop('pagina', None)

    return {
        'pagina': pagina,
        'filtros': filtros,
        'qs': params.urlencode(),
        'hay_filtros': any(
            request.GET.get(k) for k in ('q', 'tema', 'municipio', 'modalidad')
        ),
    }


def tramites(request):
    """Listado con filtros por texto, tema, municipio y modalidad."""
    return render(
        request, 'tramites/lista.html', contexto_lista_tramites(request)
    )


def tramite_detalle(request, pk):
    """Ficha completa: organismo, requisitos y enlaces oficiales."""
    tramite = get_object_or_404(
        Tramite.objects.select_related('municipio', 'organismo', 'tema')
        .prefetch_related('requisitos', 'enlaces'),
        pk=pk, activo=True,
    )
    relacionados = (
        Tramite.objects
        .filter(activo=True, tema=tramite.tema)
        .select_related('municipio', 'tema')
        .exclude(pk=tramite.pk)[:3]
    )
    return render(request, 'tramites/detalle.html', {
        'tramite': tramite,
        'relacionados': relacionados,
    })
