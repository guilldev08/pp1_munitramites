"""Utilidad temporal: listar links y texto visible de portales oficiales."""
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

URL = sys.argv[1]
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def main():
    r = requests.get(URL, timeout=40, headers=HEADERS)
    print('STATUS', r.status_code, 'FINAL', r.url, 'BYTES', len(r.content))
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    print('\nTITULO:', (soup.title.string or '').strip() if soup.title else '')
    print('\nTEXTO:')
    texto = ' '.join(soup.get_text(' ', strip=True).split())
    print(texto[:6000])
    print('\nLINKS:')
    vistos = set()
    for a in soup.find_all('a', href=True):
        href = urljoin(r.url, a['href'])
        label = ' '.join(a.get_text(' ', strip=True).split())
        if not label:
            label = '[sin texto]'
        clave = (href, label)
        if clave in vistos:
            continue
        vistos.add(clave)
        print(f'{label}\t{href}')


if __name__ == '__main__':
    main()
