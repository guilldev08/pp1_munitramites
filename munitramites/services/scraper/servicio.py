"""Orquestación del scraping: organismo → links → fichas → trámites.

El management command `scrapear_sitios` es una cáscara fina sobre esto.
Todo lo que se crea queda INACTIVO: se revisa y se publica desde el
Centro de Trámites del panel.
"""

import time

from bs4 import BeautifulSoup
from django.db import transaction

from munitramites.models import Enlace, Requisito, Tramite

from . import planilla
from .busqueda import rastreo
from .busqueda.relevancia import normalizar, normalizar_url
from .fichas import clasificacion, extraccion

# Cuántas páginas de entrada se siguen por sitio (la home ya se miró):
# los portales esconden las fichas a dos o tres clicks.
MAXIMO_PUERTAS = 6


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
    # scrapea también y se suman sus links. Y de cada puerta se miran sus
    # propias puertas: los portales esconden las fichas a dos o tres
    # clicks de la home (con tope, para no recorrer el sitio entero).
    pendientes = rastreo.puertas(html, organismo.sitio)
    vistas = {organismo.sitio}
    miradas = 0
    while pendientes and miradas < MAXIMO_PUERTAS:
        puerta = pendientes.pop(0)
        if puerta in vistas:
            continue
        vistas.add(puerta)
        miradas += 1
        html_puerta = rastreo.traer(puerta)
        if espera:
            time.sleep(espera)
        if not html_puerta:
            continue
        candidatos += rastreo.candidatos(html_puerta, puerta)
        pendientes += [
            sub for sub in rastreo.puertas(html_puerta, puerta)
            if sub not in vistas
        ]

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
            if ya_cargado(candidato):
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


def ya_cargado(candidato):
    """La misma ficha ya está cargada (URL normalizada): no duplicar.

    Se compara sin esquema, sin `www`, sin barra final y sin fragmento:
    `/tramites/dni/` y `http://www.x.gob.ar/tramites/dni` son la misma
    página y no pueden ser dos trámites.
    """
    clave = normalizar_url(candidato['url'])
    existentes = (
        Tramite.objects.exclude(enlace_oficial='')
        .values_list('enlace_oficial', flat=True)
    )
    return any(normalizar_url(url) == clave for url in existentes)


def titulo_repetido(titulo):
    """Ya hay un trámite con ese nombre: no se repite la información.

    Se compara normalizado (sin acentos ni mayúsculas) y contra TODOS los
    organismos: si el mismo trámite aparece en cinco sitios, se carga una
    sola vez.
    """
    clave = normalizar(titulo)
    existentes = Tramite.objects.values_list('titulo', flat=True)
    return any(normalizar(nombre) == clave for nombre in existentes)


def crear_tramite(candidato, organismo, espera=0.0):
    """Entra a la página del link y arma el trámite con sus requisitos.

    Devuelve False si la página no contesta, no es la ficha de un
    trámite, o el trámite ya existe (misma URL o mismo nombre): no se
    inventa ni se repite información.
    """
    pagina = rastreo.traer(candidato['url'])
    if espera:
        time.sleep(espera)
    if not pagina:
        return False

    sopa = BeautifulSoup(pagina, 'html.parser')
    if not extraccion.parece_ficha(sopa):
        return False

    titulo = extraccion.titulo(
        sopa, candidato['texto'], candidato['url'], evitar=organismo.nombre,
    )
    if titulo_repetido(titulo):
        return False

    descripcion = extraccion.descripcion(sopa)
    requisitos = extraccion.requisitos(sopa)
    if not descripcion and not requisitos:
        # Sin descripción propia ni requisitos: es una noticia o una
        # página de relleno, no la ficha de un trámite.
        return False
    descripcion = descripcion or f'Trámite informado por {organismo.nombre}.'
    enlace_turnos, enlace_oficial = extraccion.enlaces(
        sopa, candidato['url'],
    )
    # Los enlaces se cargan como botones con nombre, igual que en el
    # panel: el admin después les cambia el texto o los borra.
    botones = []
    if enlace_turnos:
        botones.append(('Pedir turno', enlace_turnos))
    if enlace_oficial:
        botones.append(('Sitio del organismo', enlace_oficial))
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
            activo=False,
        )
        for orden, texto in enumerate(requisitos, 1):
            Requisito.objects.create(
                tramite=tramite, descripcion=texto, orden=orden,
            )
        for orden, (nombre, url) in enumerate(botones):
            Enlace.objects.create(
                tramite=tramite, nombre=nombre, url=url, orden=orden,
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
