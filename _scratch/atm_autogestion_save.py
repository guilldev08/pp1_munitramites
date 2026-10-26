from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = {
    'atm_ib_auto': 'https://atmisiones.gob.ar/ingresos-brutos-autogestion/',
    'atm_inm_auto': 'https://atmisiones.gob.ar/inmobiliario-autogestion/',
    'atm_auto_auto': 'https://atmisiones.gob.ar/automotor-autogestion/',
    'atm_sellos_auto': 'https://atmisiones.gob.ar/sellos-autogestion/',
    'atm_cfr_auto': 'https://atmisiones.gob.ar/control-fiscal-en-ruta-autogestion/',
    'atm_frecuentes_auto': 'https://atmisiones.gob.ar/tramites-frecuentes-autogestion/',
}
OUT = Path('/tmp/relevamiento')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
for name, url in PAGES.items():
    r = requests.get(url, timeout=45, headers=HEADERS)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    texto = '\n'.join(
        line.strip()
        for line in soup.body.get_text('\n', strip=True).splitlines()
        if line.strip()
    )
    (OUT / f'{name}.txt').write_text(texto, encoding='utf-8')
    print(name, len(texto))
