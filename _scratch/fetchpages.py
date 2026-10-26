"""Utilidad temporal: guardar texto de páginas oficiales para relevamiento."""
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = {
    'atm_ib': 'https://atmisiones.gob.ar/ingresos-brutos/',
    'atm_inmobiliario': 'https://atmisiones.gob.ar/impuestos-inmobiliarios/',
    'atm_vehiculos': 'https://atmisiones.gob.ar/vehiculos/',
    'atm_sellos': 'https://atmisiones.gob.ar/sellos/',
    'atm_control': 'https://atmisiones.gob.ar/control-fiscal-en-ruta/',
    'atm_tasas': 'https://atmisiones.gob.ar/tasas-y-sellos/',
    'atm_otros': 'https://atmisiones.gob.ar/otros-tramites/',
    'atm_atencion': 'https://atmisiones.gob.ar/atencion-al-publico/',
    'iprodha_guia': 'https://iprodha.misiones.gob.ar/guia-de-tramites/',
    'iprodha_requisitos': 'https://iprodha.misiones.gob.ar/requisitos-de-inscripcion/',
    'iprodha_pagos': 'https://iprodha.misiones.gob.ar/formas-de-pago/',
    'energia_guia': 'https://www.energiademisiones.com.ar/guia-de-tramites/',
    'energia_tarifa': 'https://www.energiademisiones.com.ar/tarifa-social/',
    'energia_electro': 'https://www.energiademisiones.com.ar/electrodependientes/',
    'energia_planos': 'https://www.energiademisiones.com.ar/planos-del-pilar/',
    'salud_habilitacion': 'https://salud.misiones.gob.ar/habilitacion-y-registros-departamento-de-saneamiento-basico/',
    'policia_tramites': 'https://policiamisiones.gob.ar/tramites-a-ciudadanos/',
    'policia_certificados': 'https://policiamisiones.gob.ar/certificados/',
    'policia_seguridad': 'https://policiamisiones.gob.ar/direccion-seguridad-privada/',
    'policia_alarmas': 'https://policiamisiones.gob.ar/sistemas-de-alarmas-y-afines/',
    'samsa_guia': 'https://samsa.com.ar/guia-de-tramites/',
    'samsa_constancia': 'https://samsa.com.ar/constancia-de-servicio/',
    'samsa_titularidad': 'https://samsa.com.ar/cambio-de-titularidad/',
    'samsa_postal': 'https://samsa.com.ar/cambios-de-datos-postales/',
    'samsa_correccion': 'https://samsa.com.ar/correccion-de-datos/',
    'pj_requisitos': 'https://personasjuridicas.misiones.gob.ar/requisitos',
}
OUT = Path('/tmp/relevamiento')
OUT.mkdir(exist_ok=True)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for name, url in PAGES.items():
    try:
        r = requests.get(url, timeout=45, headers=HEADERS)
        print(name, r.status_code, len(r.content), r.url)
        r.raise_for_status()
    except Exception as error:
        print('ERROR', name, url, error)
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
    print('  chars', len(texto))
