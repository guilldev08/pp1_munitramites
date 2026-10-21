"""La etiqueta {% estatico %} versiona los CSS y JS para romper la caché."""

from django.template import Context, Template
from django.test import SimpleTestCase


class EstaticoTests(SimpleTestCase):

    def _render(self, ruta):
        plantilla = Template(
            '{% load estaticos %}{% estatico "' + ruta + '" %}'
        )
        return plantilla.render(Context())

    def test_agrega_la_fecha_de_modificacion(self):
        url = self._render('js/app.js')

        self.assertTrue(url.startswith('/static/js/app.js?v='), url)
        self.assertTrue(url.rsplit('=', 1)[1].isdigit(), url)

    def test_un_archivo_que_no_existe_no_rompe(self):
        self.assertEqual(
            self._render('js/no-existe.js'), '/static/js/no-existe.js',
        )
