import requests
from bs4 import BeautifulSoup

urls = [
    'https://iprodha.misiones.gob.ar/viviendas-2/',
    'https://iprodha.misiones.gob.ar/programas-con-municipios-req/',
    'https://iprodha.misiones.gob.ar/programas-personal-req/',
    'https://iprodha.misiones.gob.ar/regularizacion-dominial-req/',
]
for url in urls:
    r = requests.get(url, timeout=30)
    soup = BeautifulSoup(r.text, 'html.parser')
    print('===', url)
    for anchor in soup.find_all('a', href=True):
        text = anchor.get_text(' ', strip=True)
        href = anchor['href']
        if text and href.startswith('https://iprodha.misiones.gob.ar/'):
            print(text[:100], '|', href)
