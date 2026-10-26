"""Utilidad temporal: guardar texto limpio de las fichas del Registro Civil."""
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = 'https://www.registrocivil.misiones.gov.ar/index.php/guia-de-tramites/'
SLUGS = [
    'solicitud-de-actas', 'tramites-de-dni', 'tramites-de-pasaporte',
    'nacimientos', 'matrimonios', 'matrimonios-extranjeros',
    'union-convivencial', 'defunciones', 'divorcio', 'oficios-judiciales',
    'oficios-judiciales/oficio-para-inscribir-un-acta',
    'oficios-judiciales/oficio-que-modifica-un-acta-original',
    'oficios-judiciales/oficio-de-busqueda',
    'inscripcion-tardia-administrativa', 'extrana-jurisdiccion',
    'rectificacion-de-actas', 'legalizacion-de-titulo', 'permiso-de-viaje',
    'unidad-portatil',
]
OUT = Path('/tmp/regcivil')
OUT.mkdir(exist_ok=True)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for slug in SLUGS:
    url = BASE + slug
    try:
        r = requests.get(url, timeout=40, headers=HEADERS)
        r.raise_for_status()
    except Exception as error:
        print(f'ERROR {slug}: {error}')
        continue
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'nav', 'header', 'footer']):
        tag.decompose()
    main = soup.find('main') or soup.find('article') or soup
    texto = '\n'.join(
        line.strip()
        for line in main.get_text('\n', strip=True).splitlines()
        if line.strip()
    )
    (OUT / f'{slug.replace("/", "_")}.txt').write_text(texto, encoding='utf-8')
    print(f'===== {slug} =====')
    print(texto[:4500])
    print()
