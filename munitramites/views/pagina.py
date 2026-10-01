"""Portada del sitio.

Junta dos cosas: el bloque de bienvenida (con la barra del chatbot) y la
misma lista de tramites con filtros que usa /tramites/.
"""

from django.shortcuts import render

from .tramites import contexto_lista_tramites


def inicio(request):
    """Portada: hero con la barra del chatbot + lista de tramites con filtros."""
    return render(request, 'inicio.html', contexto_lista_tramites(request))
