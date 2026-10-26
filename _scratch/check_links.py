# -*- coding: utf-8 -*-
"""Comprueba los enlaces publicos del dataset (script temporal)."""

import concurrent.futures
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dataset  # noqa: E402

URLS = sorted({url for ficha in dataset.TRAMITES for _, url in ficha['enlaces']})


def check(url):
    try:
        response = requests.get(
            url,
            timeout=25,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 Munitramites/1.0'},
        )
        return (url, response.status_code, response.url,
                response.headers.get('content-type', ''))
    except Exception as exc:  # noqa: BLE001
        return (url, 'ERR', f'{type(exc).__name__}: {exc}'[:180], '')


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check, URLS))
    for url, status, final, content_type in results:
        print(f'{status}\t{url}\t{final}\t{content_type}')
    summary = {}
    for _, status, _, _ in results:
        summary[str(status)] = summary.get(str(status), 0) + 1
    print('SUMMARY', summary)


if __name__ == '__main__':
    main()
