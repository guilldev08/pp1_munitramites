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
    · la home del sitio, que no es un trámite,
    · listados de tema («/tema/…») y slugs de titular («samsa-instala-
      nuevo-equipamiento…»): son noticias o categorías, no trámites,
    · noticias, categorías, PDFs, redes y URLs de más de 290 caracteres,
    · páginas que no contestan o que no traen ni descripción propia ni
      requisitos: no se inventa un trámite de relleno.

Y qué NO se repite (nada redundante):

    · la misma ficha, comparando la URL sin `www`, sin barra final y
      sin fragmento (`/tramites/dni/` y `http://www.x.gob.ar/tramites/dni`
      son la misma página),
    · el mismo nombre de trámite, aunque venga de otro organismo,
    · el mismo requisito dos veces.

Los datos se leen del CONTENIDO de la ficha: el nombre sale del
`<title>`/`<h1>` de la página (no del texto del link, que en los
portales arrastra el menú), los requisitos de la lista que sigue a
«Requisitos», la descripción del primer párrafo con sustancia, y los
enlaces de turno y de la página oficial de la propia ficha.

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
