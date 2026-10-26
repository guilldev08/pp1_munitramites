import re
import sys
from pathlib import Path

import requests

urls = sys.argv[1:]
out = Path('/tmp/jina')
out.mkdir(exist_ok=True)
for url in urls:
    target = 'https://r.jina.ai/' + url
    try:
        r = requests.get(target, timeout=90, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        name = re.sub(r'[^a-zA-Z0-9]+', '_', url)[-80:].strip('_')
        (out / f'{name}.txt').write_text(r.text, encoding='utf-8')
        print('OK', url, len(r.text), out / f'{name}.txt')
    except Exception as error:
        print('ERR', url, error)
