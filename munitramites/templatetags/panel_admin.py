"""Etiquetas del panel de administración.

Se cargan en las plantillas de /admin/ con `{% load panel_admin %}`.
"""

from django import template
from django.contrib.auth.models import User

from ..models import Consulta, Municipio, Organismo, Tramite

register = template.Library()


@register.inclusion_tag('admin/panel_resumen.html', takes_context=True)
def panel_admin(context):
    """Tarjetas de resumen del índice del panel.

    Cuenta lo importante del día (trámites activos, consultas sin responder,
    sugerencias, cuentas y organismos) y lo devuelve a la plantilla
    `admin/panel_resumen.html`, que arma los enlaces a cada listado.

    Se ejecuta solo al abrir el índice: el resto de las páginas del panel no
    pagan estas consultas.
    """
    usuario = context.get('user')
    consultas = Consulta.objects

    return {
        'tramites_activos': Tramite.objects.filter(activo=True).count(),
        'tramites_total': Tramite.objects.count(),
        'pendientes': consultas.filter(estado=Consulta.Estado.PENDIENTE).count(),
        'consultas_total': consultas.count(),
        'sugerencias': consultas.filter(tipo=Consulta.Tipo.SUGERENCIA).count(),
        'usuarios': User.objects.filter(is_active=True).count(),
        'organismos': Organismo.objects.count(),
        'municipios': Municipio.objects.count(),
        # Cada tarjeta solo se muestra a quien puede entrar a ese listado.
        'puede_ver_tramites': usuario is not None and usuario.has_perm(
            'munitramites.change_tramite'
        ),
        'puede_gestionar_consultas': usuario is not None and usuario.has_perm(
            'munitramites.change_consulta'
        ),
        'puede_ver_organismos': usuario is not None and usuario.has_perm(
            'munitramites.change_organismo'
        ),
        'puede_ver_usuarios': usuario is not None and usuario.is_superuser,
    }
