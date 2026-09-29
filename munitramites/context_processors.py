"""
Context processors. >>> VARIABLES DISPONIBLES EN TODOS LOS TEMPLATES <<<

Se registran en settings.TEMPLATES['OPTIONS']['context_processors'].
Solo agregá acá cosas que necesiten TODAS las paginas.
"""

from .forms import RegistroForm


def formularios_modales(request):
    """Formulario de registro fresco para la pestaña «Crear cuenta» del modal.

    La vista de registro (views.registro) manda uno ya validado con el nombre
    `form_registro` cuando el POST tiene errores: como el contexto de la vista
    pisa al del processor, el modal muestra los errores en vez de campos vacios.

    A los usuarios logueados no les interesa, asi que no se arma el form.
    """
    if request.user.is_authenticated:
        return {}
    return {'form_registro': RegistroForm()}
