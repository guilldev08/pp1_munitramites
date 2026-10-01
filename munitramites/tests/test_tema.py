"""Tema claro/oscuro: el interruptor, el CSS y el contraste de los dos."""

import re
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from .base import TestCase

# Archivo único de estilos del sitio (STATICFILES_DIRS apunta a static/).
CSS = Path(settings.BASE_DIR) / 'static' / 'css' / 'app.css'

# Pares de color medidos: (qué se lee, color del texto, color de fondo).
# Texto plano sobre fondo = 4,5:1 mínimo (WCAG AA); el texto grande de las
# burbujas y los iconos pasan con menos, pero acá se mide el peor caso.
PARES = [
    ('texto principal sobre la página', 'gris-900', 'gris-50'),
    ('texto secundario sobre la página', 'gris-500', 'gris-50'),
    ('texto secundario sobre una tarjeta', 'gris-500', 'sup'),
    ('texto sobre la banda alterna', 'gris-500', 'gris-100'),
    ('paginación inactiva', 'gris-400', 'gris-50'),
    ('enlaces sobre la página', 'enlace', 'gris-50'),
    ('enlaces sobre una tarjeta', 'enlace', 'sup'),
    ('nav activa y píldoras azules', 'azul-txt', 'azul-claro'),
    ('etiqueta «virtual»', 'verde', 'verde-claro'),
    ('etiqueta «presencial»', 'ambar', 'ambar-claro'),
    ('etiqueta «mixta»', 'violeta-txt', 'violeta-bg'),
    ('etiqueta «cerrada»', 'gris-500', 'gris-100'),
    ('errores de formulario', 'rojo-txt', 'sup'),
    ('letra blanca del botón primario', 'ffffff', 'azul'),
    ('chips y etiquetas de datos', 'gris-700', 'sup'),
    ('pie de página', 'pie-texto', 'pie-fondo'),
]


def _luminancia(hexa):
    """Luminancia relativa de un color hex (#rgb o #rrggbb), WCAG 2.1."""
    h = hexa.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    canales = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        c = c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        canales.append(c)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def _contraste(color_a, color_b):
    """Ratio de contraste entre dos colores (1 = mismo color, 21 = blanco/negro)."""
    la, lb = _luminancia(color_a), _luminancia(color_b)
    mas_claro, mas_oscuro = max(la, lb), min(la, lb)
    return (mas_claro + 0.05) / (mas_oscuro + 0.05)


def _variables(bloque):
    """{'--gris-50': '#d4dce7', ...} a partir del texto de un bloque CSS."""
    return dict(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;', bloque))


def _bloque(selector):
    """Texto entre llaves del primer bloque que arranca con `selector`."""
    m = re.search(re.escape(selector) + r'\s*\{(.*?)\n\}', CSS.read_text(encoding='utf-8'), re.S)
    if not m:
        raise AssertionError(f'el CSS no tiene el bloque {selector}')
    return m.group(1)


class InterruptorTest(TestCase):
    """El botón de tema se pinta en todas las páginas (hereda base.html)."""

    def test_las_paginas_traen_el_interruptor(self):
        for nombre in ('inicio', 'tramites', 'chatbot', 'login'):
            with self.subTest(vista=nombre):
                r = self.client.get(reverse(nombre))
                self.assertContains(r, 'id="cambiar-tema"')
                self.assertContains(r, 'aria-label="Cambiar al tema oscuro"')

    def test_el_tema_se_aplica_antes_de_pintar(self):
        """base.html fija data-tema en <head>: si no, parpadea el otro tema."""
        r = self.client.get(reverse('inicio'))
        html = r.content.decode()
        self.assertIn("localStorage.getItem('munitramites-tema')", html)
        self.assertIn('prefers-color-scheme: dark', html)
        self.assertIn("document.documentElement.setAttribute('data-tema'", html)
        # el script tiene que estar antes del <body>, o sea antes de pintar
        self.assertLess(html.index("setAttribute('data-tema'"), html.index('<body>'))


class CssTest(TestCase):
    """El CSS declara los dos temas y el botón que los voltea."""

    def test_trae_el_bloque_oscuro(self):
        css = CSS.read_text(encoding='utf-8')
        self.assertIn(':root[data-tema="oscuro"]', css)
        self.assertIn('color-scheme: dark', css)
        # tokens que usan las tarjetas, los enlaces y el pie
        self.assertIn('--sup', _bloque(':root'))
        self.assertIn('--enlace', _bloque(':root'))

    def test_el_interruptor_tiene_estilo(self):
        css = CSS.read_text(encoding='utf-8')
        self.assertIn('.tema-boton', css)


class ContrasteTest(TestCase):
    """WCAG AA (4,5:1) medido sobre los hex que declara el CSS.

    Lee el archivo de verdad (no una copia): si alguien mueve un gris,
    el test se entera en lugar de enterarse el que está leyendo la pantalla.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.claro = _variables(_bloque(':root'))
        cls.oscuro = dict(cls.claro, **_variables(_bloque(':root[data-tema="oscuro"]')))

    def _ver(self, variables, tema):
        for descripcion, texto, fondo in PARES:
            with self.subTest(tema=tema, par=descripcion):
                a = variables.get('--' + texto, '#' + texto)
                b = variables.get('--' + fondo, '#' + fondo)
                ratio = _contraste(a, b)
                self.assertGreaterEqual(
                    ratio, 4.5,
                    f'{descripcion}: {a} sobre {b} da {ratio:.2f}:1 (mínimo 4,5)')

    def test_tema_claro_cumple_wcag(self):
        self._ver(self.claro, 'claro')

    def test_tema_oscuro_cumple_wcag(self):
        self._ver(self.oscuro, 'oscuro')

    def test_el_oscuro_no_es_el_claro(self):
        """Trampa: el bloque oscuro tiene que cambiar el fondo de verdad."""
        self.assertNotEqual(self.oscuro['--gris-50'], self.claro['--gris-50'])
        self.assertNotEqual(self.oscuro['--sup'], self.claro['--sup'])
