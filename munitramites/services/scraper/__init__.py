"""Scraping de sitios oficiales: de la planilla a trámites inactivos.

Tres etapas, misma idea que services/chatbot/:

    1. PLANILLA    services/scraper/planilla.py
                   Lee data/organismos_misiones.csv (NOMBRE, OCUPACION,
                   LINK_SITIO_OFICIAL) y crea los organismos que falten.
                   Idempotente.

    2. RASTREO     services/scraper/rastreo.py + relevancia.py
                   Visita cada sitio, puntúa los links y sigue solo los
                   que huelen a trámite. Si el portal esconde los
                   trámites detrás de una «puerta» (Servicios, Trámites,
                   Turnos…), entra y busca también ahí.

    3. EXTRACCION  services/scraper/extraccion.py + clasificacion.py
                   De la ficha saca título, descripción y requisitos, y
                   deduce tema, municipio y modalidad.

    ORQUESTAR      services/scraper/servicio.py

Qué NO se toma (el «tomaba cualquier cosa» viejo):

    · links de menú sueltos («Servicios», «Registro»): valen la mitad,
    · páginas que son un índice/sección y no la ficha de un trámite,
    · noticias, categorías, PDFs, redes y URLs de más de 290 caracteres,
    · páginas que no contestan: no se inventa un trámite de relleno.

Todo lo que sale queda INACTIVO: se revisa, se corrige y se publica
desde el Centro de Trámites del panel.

Uso típico (el management command es una cáscara fina sobre esto):

    from munitramites.services import scraper
    organismos, creados, actualizados = scraper.importar_planilla()
    creados, omitidos, caidos = scraper.scrapear(organismos)

Tests: munitramites/tests/test_scraping.py.
"""

from .planilla import PLANILLA, importar as importar_planilla
from .servicio import scrapear, scrapear_organismo

__all__ = ['PLANILLA', 'importar_planilla', 'scrapear', 'scrapear_organismo']
