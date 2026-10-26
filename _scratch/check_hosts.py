# -*- coding: utf-8 -*-
"""Prueba variantes de enlaces que fallaron (script temporal)."""

import requests

URLS = [
    'https://personasjuridicas.misiones.gob.ar/requisitos/',
    'http://personasjuridicas.misiones.gob.ar/requisitos/',
    'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/05/PERSONAS-HUMANAS-QUE-REALIZAN-ACTIVIDAD-ECONOMICA.pdf',
    'http://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/05/PERSONAS-HUMANAS-QUE-REALIZAN-ACTIVIDAD-ECONOMICA.pdf',
    'https://salud.misiones.gob.ar/',
    'http://salud.misiones.gob.ar/',
    'https://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES.pdf',
    'http://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES.pdf',
    'https://posadas.gob.ar/',
    'https://posadas.gob.ar/guiatramite',
    'https://www.posadas.gob.ar/guiatramite',
]

for url in URLS:
    try:
        response = requests.get(
            url,
            timeout=25,
            allow_redirects=False,
            headers={'User-Agent': 'Mozilla/5.0 Munitramites/1.0'},
        )
        print(f'{response.status_code}\t{url}\t{response.headers.get("location", "")}')
    except Exception as exc:  # noqa: BLE001
        print(f'ERR\t{url}\t{type(exc).__name__}: {exc}')
