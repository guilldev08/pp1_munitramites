"""Landing del sitio.

La página de entrada ya no es la portada con el listado: es una landing
propia, con el hero y las dos puertas de entrada («Iniciar sesión» abre el
modal de auth; «Continuar sin sesión» entra al sitio) más la sección
«¿Cómo funciona?», que aparece sola cuando el visitante baja un poco.

El listado de trámites con filtros vive en /tramites/ (ver
views/tramites.py) y la barra del asistente se retira de la landing por
ahora: el asistente sigue al alcance con el botón 💬 y en /chatbot/.
"""

from django.shortcuts import render


def inicio(request):
    """Landing: hero con los botones de ingreso + los tres pasos."""
    return render(request, 'inicio.html')
