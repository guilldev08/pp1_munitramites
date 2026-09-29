"""API liviana del sitio (JSON, sin sesion ni templates)."""

from django.http import JsonResponse

from ..models import Tramite


def api_tramites(request):
    """Listado liviano de tramites. Util para integraciones."""
    datos = [
        {
            'id': t.pk,
            'titulo': t.titulo,
            'tema': t.tema,
            'modalidad': t.modalidad,
            'municipio': t.municipio.nombre,
            'organismo': t.organismo.nombre,
        }
        for t in Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo')
    ]
    return JsonResponse({'count': len(datos), 'tramites': datos})
