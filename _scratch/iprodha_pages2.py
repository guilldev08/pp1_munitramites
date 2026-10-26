from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = {
    'iprodha_rurales': 'https://iprodha.misiones.gob.ar/construccion-de-viviendas-rurales-2/',
    'iprodha_compartida': 'https://iprodha.misiones.gob.ar/construccion-de-viviendas-de-gestion-compartida/',
    'iprodha_arreglo': 'https://iprodha.misiones.gob.ar/arreglo-mi-casa/',
    'iprodha_construyo': 'https://iprodha.misiones.gob.ar/construyo-mi-casa/',
    'iprodha_mediacion': 'https://iprodha.misiones.gob.ar/requisitos-mediacion-entre-terceros/',
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
    print(texto[:4500])
