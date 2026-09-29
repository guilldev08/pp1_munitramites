"""Portada del sitio.

Junta dos cosas: el bloque de bienvenida (con la barra del chatbot) y la
misma lista de tramites con filtros que usa /tramites/.
"""

from django.db.models import Count
from django.shortcuts import render

from ..models import Municipio, Organismo, Requisito, Tramite
from .tramites import contexto_lista_tramites


def inicio(request):
    """Portada: hero con la barra del chatbot + lista de tramites con filtros."""
    context = {
        'total_tramites': Tramite.objects.filter(activo=True).count(),
        'total_organismos': Organismo.objects.count(),
        'total_municipios': Municipio.objects.count(),
        'total_requisitos': Requisito.objects.count(),
        'temas': (
            Tramite.objects.filter(activo=True)
            .values('tema')
            .annotate(total=Count('id'))
            .order_by('tema')
        ),
    }
    context.update(contexto_lista_tramites(request))
    return render(request, 'inicio.html', context)
