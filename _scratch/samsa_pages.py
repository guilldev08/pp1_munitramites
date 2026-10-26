from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = {
    'samsa_cambio_titularidad': 'https://samsa.com.ar/cambio-de-titularidad/',
    'samsa_datos_postales': 'https://samsa.com.ar/cambios-de-datos-postales/',
    'samsa_correccion_datos': 'https://samsa.com.ar/correccion-de-datos/',
    'samsa_constancia': 'https://samsa.com.ar/constancia-de-servicio/',
    'samsa_libre_deuda': 'https://samsa.com.ar/libre-deuda/',
    'samsa_tapada': 'https://samsa.com.ar/v1/solicitud-de-nivel-de-tapada-de-cloaca/',
    'samsa_visado': 'https://samsa.com.ar/visado-de-planos/',
    'samsa_conexion': 'https://samsa.com.ar/solicitud-conexion-domiciliaria/',
    'samsa_desconexion': 'https://samsa.com.ar/v1/solicitud-de-desconexion/',
    'samsa_convenio': 'https://samsa.com.ar/convenio-de-pago/',
    'samsa_debito': 'https://samsa.com.ar/adhesion-debito-automatico/',
    'samsa_agua_bloque': 'https://samsa.com.ar/venta-de-agua-en-bloque/',
    'samsa_analisis': 'https://samsa.com.ar/analisis-de-agua-para-terceros/',
    'samsa_nivelacion': 'https://samsa.com.ar/nivelacion-de-medidor/',
    'samsa_descarga': 'https://samsa.com.ar/descarga-de-liquidos-cloacales/',
    'samsa_reparacion': 'https://samsa.com.ar/solicitud-de-reparacion/',
    'samsa_factibilidad': 'https://samsa.com.ar/solicitud-de-factibilidad-para-barrios/',
    'samsa_cierre': 'https://samsa.com.ar/solicitud-de-cierre-de-llave-maestra/',
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
    print(texto[:3500])
