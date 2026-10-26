from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = {
    'iprodha_trasplantados': 'https://iprodha.misiones.gob.ar/beneficio-para-personas-trasplantadas/',
    'iprodha_cud': 'https://iprodha.misiones.gob.ar/beneficios-cud/',
    'iprodha_fallecimiento': 'https://iprodha.misiones.gob.ar/cancelacion-por-fallecimiento/',
    'iprodha_anticipada': 'https://iprodha.misiones.gob.ar/cancelacion-anticipada/',
    'iprodha_titular': 'https://iprodha.misiones.gob.ar/cambio-de-titular/',
    'iprodha_siniestro': 'https://iprodha.misiones.gob.ar/denuncia-de-siniestro/',
    'iprodha_renuncia': 'https://iprodha.misiones.gob.ar/renuncia-la-vivienda/',
    'iprodha_custodia': 'https://iprodha.misiones.gob.ar/permiso-de-custodia-o-guarda/',
    'iprodha_viviendas': 'https://iprodha.misiones.gob.ar/viviendas-2/',
    'iprodha_municipios': 'https://iprodha.misiones.gob.ar/programas-con-municipios-req/',
    'iprodha_personal': 'https://iprodha.misiones.gob.ar/programas-personal-req/',
    'iprodha_regularizacion': 'https://iprodha.misiones.gob.ar/regularizacion-dominial-req/',
}
OUT = Path('/tmp/relevamiento')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
for name, url in PAGES.items():
    try:
        r = requests.get(url, timeout=45, headers=HEADERS)
        print('====', name, r.status_code, len(r.content), r.url)
        r.raise_for_status()
    except Exception as error:
        print('ERR', name, error)
        continue
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'nav', 'header', 'footer']):
        tag.decompose()
    main = soup.find('main') or soup.find('article') or soup.body or soup
    texto = '\n'.join(
        line.strip()
        for line in main.get_text('\n', strip=True).splitlines()
        if line.strip()
    )
    (OUT / f'{name}.txt').write_text(texto, encoding='utf-8')
    print(texto[:5000])
