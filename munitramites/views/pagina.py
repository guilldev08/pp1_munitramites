"""Portada del sitio.

Junta dos cosas: el bloque de bienvenida (con la barra del chatbot) y la
misma lista de tramites con filtros que usa /tramites/.
"""

from django.db.models import Count
from django.shortcuts import render

from ..models import Tramite
from .tramites import contexto_lista_tramites


def inicio(request):
    """Portada: hero con la barra del chatbot + lista de tramites con filtros."""
    context = {
        # Contadores por tema, para la nube «Explorar por tema»
        'temas': (
            Tramite.objects.filter(activo=True)
            .values('tema')
            .annotate(total=Count('id'))
            .order_by('tema')
        ),
    }
    context.update(contexto_lista_tramites(request))
    return render(request, 'inicio.html', context)
