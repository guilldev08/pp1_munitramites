"""API liviana del sitio (JSON, sin sesion ni templates)."""

from django.http import JsonResponse

from ..models import Tramite


def api_tramites(request):
    """Listado liviano de tramites. Util para integraciones."""
    datos = [
        {
            'id': t.pk,
            'titulo': t.titulo,
            'tema': str(t.tema),
            'modalidad': t.modalidad,
            'municipio': t.municipio.nombre,
            'organismo': t.organismo.nombre,
            'direcciones': [
                {
                    'lugar': d.lugar,
                    'municipio': d.municipio.nombre,
                    'direccion': d.direccion,
                }
                for d in t.direcciones.all()
            ],
        }
        for t in Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo', 'tema')
        .prefetch_related('direcciones__municipio')
    ]
    return JsonResponse({'count': len(datos), 'tramites': datos})
