import re
import sys

import requests
from bs4 import BeautifulSoup

url = sys.argv[1]
r = requests.get(url, timeout=40, headers={'User-Agent': 'Mozilla/5.0'})
r.raise_for_status()
r.encoding = r.apparent_encoding
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    texto = ' '.join(a.get_text(' ', strip=True).split())
    href = a['href']
    if texto:
        print(f'{texto[:100]}\t{href}')
