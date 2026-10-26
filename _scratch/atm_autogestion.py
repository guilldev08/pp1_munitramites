import requests
from bs4 import BeautifulSoup

urls = [
    'https://atmisiones.gob.ar/ingresos-brutos-autogestion/',
    'https://atmisiones.gob.ar/inmobiliario-autogestion/',
    'https://atmisiones.gob.ar/automotor-autogestion/',
    'https://atmisiones.gob.ar/sellos-autogestion/',
    'https://atmisiones.gob.ar/control-fiscal-en-ruta-autogestion/',
    'https://atmisiones.gob.ar/tramites-frecuentes-autogestion/',
]
for url in urls:
    try:
        r = requests.get(url, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        print('====', url, r.status_code, len(r.content))
        print(' '.join(soup.get_text(' ', strip=True).split())[:3000])
    except Exception as error:
        print('ERR', url, error)
