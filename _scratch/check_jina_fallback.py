# -*- coding: utf-8 -*-
"""Prueba los enlaces de respaldo con r.jina.ai (script temporal)."""

import requests

URLS = [
    'https://r.jina.ai/https://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES.pdf',
    'https://r.jina.ai/https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/05/PERSONAS-HUMANAS-QUE-REALIZAN-ACTIVIDAD-ECONOMICA.pdf',
    'https://r.jina.ai/https://posadas.gob.ar/guiatramite',
    'https://r.jina.ai/https://posadas.gob.ar/ajaxGuiatramiteDatos',
]

for url in URLS:
    try:
        response = requests.get(
            url,
            timeout=60,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 Munitramites/1.0'},
        )
        print(response.status_code, len(response.text), url)
        print(response.text[:180].replace('\n', ' '))
    except Exception as exc:  # noqa: BLE001
        print('ERR', url, type(exc).__name__, str(exc)[:160])
