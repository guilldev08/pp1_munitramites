"""Utilidad temporal: bajar las fichas de la guía de trámites de Posadas."""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = 'https://posadas.gob.ar/guiatramite'
OUT = Path('/tmp/posadas')
OUT.mkdir(exist_ok=True)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': URL,
    'X-Requested-With': 'XMLHttpRequest',
}

r = requests.get(URL, timeout=40, headers=HEADERS)
r.raise_for_status()
ids = sorted({int(x) for x in re.findall(r'mostrarTramite\((\d+)\)', r.text)})
print('IDS', ids)

for idtramite in ids:
    response = requests.post(
        'https://posadas.gob.ar/ajaxGuiatramiteDatos',
        data={'idtramite': idtramite},
        timeout=40,
        headers=HEADERS,
    )
    response.raise_for_status()
    (OUT / f'{idtramite}.html').write_text(response.text, encoding='utf-8')
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    texto = '\n'.join(
        line.strip()
        for line in soup.get_text('\n', strip=True).splitlines()
        if line.strip()
    )
    (OUT / f'{idtramite}.txt').write_text(texto, encoding='utf-8')
    print(f'===== {idtramite} =====')
    print(texto[:3000])
