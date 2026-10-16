"""Orquestación del scraping: organismo → links → fichas → trámites.

El management command `scrapear_sitios` es una cáscara fina sobre esto.
Todo lo que se crea queda INACTIVO: se revisa y se publica desde el
Centro de Trámites del panel.
"""

import time

from bs4 import BeautifulSoup
from django.db import transaction

from munitramites.models import Requisito, Tramite

from . import clasificacion, extraccion, planilla, rastreo


def scrapear_organismo(organismo, max_por_sitio=8, espera=0.6, avisar=None):
    """Scrapea un sitio y crea sus trámites.

    Devuelve (creados, omitidos), o None si el sitio no contestó.
    `avisar(mensaje, error=False)` recibe las novedades de la corrida.
    """
    avisar = avisar or (lambda mensaje, error=False: None)
    if not organismo.sitio:
        return 0, 0

    html = rastreo.traer(organismo.sitio)
    if html is None:
        avisar(
            f'  ! {organismo.nombre}: no se pudo leer {organismo.sitio}',
            error=True,
        )
        return None
    if espera:
        time.sleep(espera)

    candidatos = rastreo.candidatos(html, organismo.sitio)

    # Segunda vuelta: si el sitio tiene puerta al portal de trámites, se
    # scrapea también y se suman sus links.
    ya_candidatos = {c['url'] for c in candidatos}
    for puerta in rastreo.puertas(html, organismo.sitio):
        if puerta in ya_candidatos:
            continue
        html_puerta = rastreo.traer(puerta)
        if espera:
            time.sleep(espera)
        if html_puerta:
            candidatos += rastreo.candidatos(html_puerta, puerta)

    # Un solo link por URL (puede repetirse entre páginas), del más
    # prometedor al resto, y hasta el máximo del sitio.
    unicos = {}
    for candidato in candidatos:
        unicos.setdefault(candidato['url'], candidato)
    lista = sorted(unicos.values(), key=lambda c: -c['puntaje'])
    candidatos = lista[:max_por_sitio]

    creados = omitidos = 0
    for candidato in candidatos:
        try:
            if ya_cargado(candidato, organismo):
                omitidos += 1
                continue
            if crear_tramite(candidato, organismo, espera):
                creados += 1
        except Exception as error:
            # Un link tonto no puede frenar la corrida entera: se anota y
            # se sigue con el siguiente.
            avisar(
                f'  ! {organismo.nombre}: no se pudo cargar '
                f'«{candidato["texto"][:60]}» ({error})',
                error=True,
            )
    return creados, omitidos


def ya_cargado(candidato, organismo):
    """Misma URL o mismo título del mismo organismo: no duplicar."""
    return Tramite.objects.filter(
        enlace_oficial=candidato['url']
    ).exists() or Tramite.objects.filter(
        titulo=extraccion.titulo(candidato['texto'], candidato['url']),
        organismo=organismo,
    ).exists()


def crear_tramite(candidato, organismo, espera=0.0):
    """Entra a la página del link y arma el trámite con sus requisitos.

    Devuelve False si la página no contesta o no es la ficha de un
    trámite (un índice de sección, una noticia…): no se inventa un
    trámite con texto de relleno.
    """
    pagina = rastreo.traer(candidato['url'])
    if espera:
        time.sleep(espera)
    if not pagina:
        return False

    sopa = BeautifulSoup(pagina, 'html.parser')
    if not extraccion.parece_ficha(sopa):
        return False

    descripcion = extraccion.descripcion(sopa, organismo.nombre)
    requisitos = extraccion.requisitos(sopa)
    titulo = extraccion.titulo(candidato['texto'], candidato['url'])
    contexto = (
        f'{organismo.nombre} {organismo.ocupacion} '
        f'{candidato["texto"]} {candidato["url"]}'
    )
    with transaction.atomic():
        tramite = Tramite.objects.create(
            titulo=titulo,
            tema=clasificacion.tema_para(contexto),
            modalidad=clasificacion.modalidad_para(contexto),
            municipio=clasificacion.municipio_para(organismo.nombre),
            organismo=organismo,
            descripcion=descripcion,
            enlace_turnos=(
                candidato['url'] if 'turno' in candidato['url'].lower()
                else ''
            ),
            enlace_oficial=candidato['url'],
            activo=False,
        )
        for orden, texto in enumerate(requisitos, 1):
            Requisito.objects.create(
                tramite=tramite, descripcion=texto, orden=orden,
            )
    return True


def scrapear(organismos, max_por_sitio=8, espera=0.6, avisar=None):
    """Scrapea una lista de organismos ya importados.

    Devuelve (creados, omitidos, sitios_caidos).
    """
    avisar = avisar or (lambda mensaje, error=False: None)
    creados = omitidos = caidos = 0
    for organismo in organismos:
        resultado = scrapear_organismo(
            organismo, max_por_sitio=max_por_sitio, espera=espera,
            avisar=avisar,
        )
        if resultado is None:
            caidos += 1
            continue
        creados_locales, omitidos_locales = resultado
        creados += creados_locales
        omitidos += omitidos_locales
        avisar(
            f'  · {organismo.nombre}: {creados_locales} trámite(s) '
            f'nuevo(s), {omitidos_locales} ya cargado(s).'
        )
    return creados, omitidos, caidos
