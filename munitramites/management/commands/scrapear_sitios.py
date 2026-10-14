"""Pobla la base con la planilla de organismos y el scraping de sus sitios.

    docker compose exec web python manage.py scrapear_sitios
    docker compose exec web python manage.py scrapear_sitios --limite 5 --max-por-sitio 3

Paso 1: importa `data/organismos_misiones.csv` (NOMBRE, OCUPACION,
LINK_SITIO_OFICIAL) y crea los organismos que falten.

Paso 2: visita cada sitio oficial, busca links con pinta de trámite
(DNI, licencia, partida, turno…), entra a los más prometedores y de ahí
extrae la descripción y los requisitos (las listas «Requisitos:»).

Todo lo que sale del scraping queda INACTIVO: se revisa, se corrige y se
publica desde el Centro de Trámites del panel. El comando es
idempotente: si se corre de nuevo, no duplica trámites ya cargados.
"""

import csv
import os
import re
import time
import unicodedata
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from munitramites.models import Municipio, Organismo, Requisito, Tema, Tramite

# Navegador común: varios sitios oficiales rechazan al agente por defecto
# de requests (el 403 de argentina.gob.ar era eso).
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Palabras que, en el texto o la URL de un link, huelen a trámite.
PALABRAS_TRAMITE = (
    'tramite', 'dni', 'pasaporte', 'partida', 'nacimiento', 'defuncion',
    'matrimonio', 'licencia', 'conducir', 'catastro', 'habilitacion',
    'certificado', 'registro', 'inscripcion', 'turno', 'subsidio', 'beca',
    'empleo', 'jubilacion', 'pension', 'vencimiento', 'carne',
    'contribucion', 'impuesto', 'tasa', 'padron', 'libreta', 'antecedente',
    'domicilio', 'discapacidad', 'vacuna', 'ambulatorio', 'personas',
    'alquiler', 'lote', 'vivienda', 'comercio', 'monotributo', 'factura',
)

# Caminos que nunca son un trámite: noticias, categorías y compañía.
PALABRAS_RUIDO = (
    '/noticia', '/noticias', '/category/', '/categoria/', '/blog',
    '/tag/', '/wp-', '/feed', '/contacto', '/privacidad', '/terminos',
    '/quienes-somos', '/galeria', '/audiovisual', '.pdf', '.doc',
)

# Redes sociales: enlaces con URL rara pero sin texto.
REDES = (
    'facebook.com', 'instagram.com', 'youtube.com', 'twitter.com',
    '://x.com/', 'linkedin', 'tiktok', 'whatsapp', 'wa.me',
)

# Puertas: los portales esconden los trámites detrás de una página de
# entrada («Servicios», «Portal del Ciudadano», «Turnos»…). Si el sitio
# tiene una, se scrapea también.
PALABRAS_PUERTA = (
    'ciudadano', 'servicio', 'tramite', 'online', 'on-line', 'turno',
    'gestion', 'mesa de entradas',
)

# Las frases de una lista que suenan a «qué hay que presentar».
PALABRAS_REQUISITO = (
    'dni', 'documento', 'original', 'copia', 'formulario', 'presentar',
    'acreditar', 'abonar', 'acompanar', 'vigente', 'certificado',
    'partida', 'constancia', 'comprobante', 'foto', 'fotocopia', 'turno',
)

# Los 7 temas del catálogo (los mismos que carga cargar_datos.py), en
# el orden en que se los prueba: gana el primero que calce.
TEMAS_POR_PALABRA = (
    ('Salud', ('salud', 'pami', 'hospital', 'vacuna', 'medic',
               'ambulatorio', 'ips', 'clinica')),
    ('Tránsito', ('transito', 'conducir', 'licencia', 'vialidad',
                  'vehiculo', 'automotor')),
    ('Impuestos', ('impuesto', 'arca', 'tribut', 'rentas', 'contaduria',
                   'recaudac', 'contribucion', 'tasa', 'monotributo')),
    ('Vivienda', ('vivienda', 'iprodha', 'habitat', 'lote', 'construccion',
                  'alquiler')),
    ('Comercio', ('comercio', 'habilitacion', 'industria', 'produccion',
                  'emprend')),
    ('Seguridad', ('seguridad', 'policia', 'bomberos', 'emergenc', '911')),
    ('Documentación', ('dni', 'pasaporte', 'partida', 'registro civil',
                       'catastro', 'estado civil', 'identificac',
                       'documento', 'personas')),
)


def _sin_acentos(texto):
    """«Oberá» → «Obera»: para comparar y para guardar igual que el seed."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )


def _traer(url):
    """HTML de una URL, o None si el sitio no contesta.

    Nunca corta el pase: un sitio caído es una fila en el resumen, no un
    traceback.
    """
    try:
        respuesta = requests.get(
            url, headers={'User-Agent': UA}, timeout=15,
        )
        respuesta.raise_for_status()
    except requests.RequestException:
        return None
    if 'html' not in respuesta.headers.get('Content-Type', 'html'):
        return None
    return respuesta.text


def _candidatos(html, base):
    """Links del sitio con pinta de trámite, del más prometedor al menos."""
    sopa = BeautifulSoup(html, 'html.parser')
    vistos, salida = set(), []
    for a in sopa.find_all('a', href=True):
        texto = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or len(texto) < 5 or url in vistos:
            continue
        # El modelo admite 300; una URL más larga que eso no entra ni
        # serviría truncada (Firebird corta en seco y tira el error).
        if len(url) > 290:
            continue
        bajo_url = _sin_acentos(url.lower())
        if any(p in bajo_url for p in PALABRAS_RUIDO + REDES):
            continue
        bajo_texto = _sin_acentos(texto.lower())
        puntaje = sum(1 for p in PALABRAS_TRAMITE if p in bajo_texto)
        puntaje += sum(1 for p in PALABRAS_TRAMITE if p in bajo_url) / 2
        if not puntaje:
            continue
        vistos.add(url)
        salida.append({'texto': texto, 'url': url, 'puntaje': puntaje})
    salida.sort(key=lambda c: -c['puntaje'])
    return salida


def _puertas(html, base, limite=3):
    """Links de entrada al portal de trámites del sitio (segunda vuelta)."""
    sopa = BeautifulSoup(html, 'html.parser')
    salida, vistos = [], set()
    for a in sopa.find_all('a', href=True):
        texto = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or url in vistos or url == base:
            continue
        if len(url) > 290:
            continue
        bajo = _sin_acentos(f'{texto} {url}'.lower())
        if any(p in bajo for p in PALABRAS_RUIDO + REDES):
            continue
        if any(p in bajo for p in PALABRAS_PUERTA):
            vistos.add(url)
            salida.append(url)
            if len(salida) == limite:
                break
    return salida


def _lista_de_requisitos(sopa):
    """La lista <ul>/<ol> que sigue al encabezado «Requisitos» (o similar)."""
    for encabezado in sopa.find_all(['h2', 'h3', 'h4']):
        rotulo = _sin_acentos(encabezado.get_text(' ', strip=True).lower())
        if 'requisit' not in rotulo and 'que necesit' not in rotulo:
            continue
        hermano = encabezado.find_next_sibling()
        while hermano is not None:
            if hermano.name in ('h2', 'h3', 'h4'):
                break
            if hermano.name in ('ul', 'ol'):
                return hermano
            if hermano.name in ('div', 'section'):
                dentro = hermano.find(['ul', 'ol'])
                if dentro:
                    return dentro
            hermano = hermano.find_next_sibling()
    return None


def _requisitos(sopa):
    """Textos de requisitos de la página, limpios y acotados."""
    lista = _lista_de_requisitos(sopa)
    if lista:
        items = [li.get_text(' ', strip=True) for li in lista.find_all('li')]
    else:
        # Respaldo: <li> sueltos con pinta de requerimiento.
        items = [
            li.get_text(' ', strip=True)
            for li in sopa.find_all('li')
            if any(p in _sin_acentos(li.get_text(' ', strip=True).lower())
                   for p in PALABRAS_REQUISITO)
        ]

    limpios, vistos = [], set()
    for item in items:
        item = re.sub(r'\s+', ' ', item).strip(' ·•-')
        clave = _sin_acentos(item.lower())
        if not (10 <= len(item) <= 290) or clave in vistos:
            continue
        vistos.add(clave)
        limpios.append(item)
        if len(limpios) == 8:
            break
    return limpios


def _descripcion(sopa, nombre_organismo):
    """Meta descripción, el primer párrafo decente, o un texto de fábrica."""
    meta = sopa.find('meta', attrs={'name': 'description'})
    if meta and len((meta.get('content') or '').strip()) > 40:
        return re.sub(r'\s+', ' ', meta['content']).strip()[:500]
    for parrafo in sopa.find_all('p'):
        if parrafo.find_parent(['header', 'footer', 'nav']):
            continue
        texto = re.sub(r'\s+', ' ', parrafo.get_text(' ', strip=True))
        if len(texto) > 60:
            return texto[:500]
    return f'Trámite informado por {nombre_organismo}.'


def _titulo_limpio(texto, url):
    """Rótulo usable para el trámite (máx. 200 caracteres en el modelo)."""
    texto = re.sub(r'\s+', ' ', texto or '').strip(' .|-–—·>“”"')
    if len(texto) < 8:
        segmento = urlparse(url).path.rstrip('/').split('/')[-1]
        texto = re.sub(r'[-_]+', ' ', segmento).strip().title() or texto
    return texto[:195] or 'Trámite'


def _tema_para(texto):
    """Tema del catálogo que mejor calce con el organismo y el link."""
    bajo = _sin_acentos(texto.lower())
    for nombre, palabras in TEMAS_POR_PALABRA:
        if any(p in bajo for p in palabras):
            return Tema.objects.get_or_create(nombre=nombre)[0]
    return Tema.objects.get_or_create(nombre='Documentación')[0]


def _municipio_para(nombre_organismo):
    """«Municipalidad de Oberá» → Obera; el resto, Posadas (sede)."""
    bajo = _sin_acentos(nombre_organismo.lower())
    for prefijo in ('municipalidad de ', 'municipio de '):
        if bajo.startswith(prefijo):
            localidad = _sin_acentos(nombre_organismo[len(prefijo):].strip())
            if localidad.lower() not in ('misiones', ''):
                return Municipio.objects.get_or_create(nombre=localidad)[0]
    return Municipio.objects.get_or_create(nombre='Posadas')[0]


def _modalidad_para(texto):
    bajo = _sin_acentos(texto.lower())
    if any(p in bajo for p in ('en linea', 'online', 'digital', 'virtual')):
        return 'virtual'
    return 'presencial'


def _importar_csv(ruta):
    """Crea (o completa) los organismos de la planilla. Idempotente."""
    organismos, creados, actualizados = [], 0, 0
    with open(ruta, encoding='utf-8-sig', newline='') as archivo:
        for fila in csv.DictReader(archivo):
            nombre = (fila.get('NOMBRE') or '').strip()
            if not nombre:
                continue
            organismo, creado = Organismo.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'direccion': 'Sin dirección informada',
                    'ocupacion': (fila.get('OCUPACION') or '').strip(),
                    'sitio': (fila.get('LINK_SITIO_OFICIAL') or '').strip(),
                },
            )
            if creado:
                creados += 1
            else:
                cambios = {}
                if not organismo.sitio and fila.get('LINK_SITIO_OFICIAL'):
                    cambios['sitio'] = fila['LINK_SITIO_OFICIAL'].strip()
                if not organismo.ocupacion and fila.get('OCUPACION'):
                    cambios['ocupacion'] = fila['OCUPACION'].strip()
                if cambios:
                    for campo, valor in cambios.items():
                        setattr(organismo, campo, valor)
                    organismo.save(update_fields=list(cambios))
                    actualizados += 1
            organismos.append(organismo)
    return organismos, creados, actualizados


class Command(BaseCommand):
    help = (
        'Importa la planilla de organismos y scrapear cada sitio oficial '
        'buscando trámites (quedan inactivos para revisar).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv', default='data/organismos_misiones.csv',
            help='Planilla a importar (NOMBRE, OCUPACION, LINK_SITIO_OFICIAL).',
        )
        parser.add_argument(
            '--limite', type=int, default=0,
            help='Procesar solo los primeros N sitios (0 = todos).',
        )
        parser.add_argument(
            '--max-por-sitio', type=int, default=8,
            help='Cuántos links con pinta de trámite se siguen por sitio.',
        )
        parser.add_argument(
            '--espera', type=float, default=0.6,
            help='Segundos de pausa entre pedido y pedido (cortesía).',
        )
        parser.add_argument(
            '--solo-organismos', action='store_true',
            help='Importa la planilla y no scrapear nada.',
        )

    def handle(self, *args, **opciones):
        ruta = opciones['csv']
        if not os.path.exists(ruta):
            raise CommandError(f'No existe la planilla: {ruta}')

        organismos, creados, actualizados = _importar_csv(ruta)
        self.stdout.write(self.style.SUCCESS(
            f'Organismos: {creados} creados, {actualizados} actualizados '
            f'(total en la planilla: {len(organismos)}).'
        ))
        if opciones['solo_organismos']:
            return

        if opciones['limite']:
            organismos = organismos[:opciones['limite']]

        creados = omitidos = con_fallo = 0
        for organismo in organismos:
            resultado = self._procesar_organismo(organismo, opciones)
            if resultado is None:
                con_fallo += 1
                continue
            creados_locales, omitidos_locales = resultado
            creados += creados_locales
            omitidos += omitidos_locales
            self.stdout.write(
                f'  · {organismo.nombre}: {creados_locales} trámite(s) '
                f'nuevo(s), {omitidos_locales} ya cargado(s).'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {creados} trámites nuevos (todos inactivos para '
            f'revisar), {omitidos} ya existían, '
            f'{con_fallo} sitio(s) no contestaron.'
        ))

    def _procesar_organismo(self, organismo, opciones):
        """Scrapea un sitio y crea sus trámites.

        Devuelve (creados, omitidos), o None si el sitio no contestó.
        """
        if not organismo.sitio:
            return 0, 0

        html = _traer(organismo.sitio)
        if html is None:
            self.stderr.write(self.style.WARNING(
                f'  ! {organismo.nombre}: no se pudo leer {organismo.sitio}'
            ))
            return None

        if opciones['espera']:
            time.sleep(opciones['espera'])

        candidatos = _candidatos(html, organismo.sitio)

        # Segunda vuelta: si el sitio tiene puerta al portal de trámites,
        # se scrapea también y se suman sus links.
        ya_candidatos = {c['url'] for c in candidatos}
        for puerta in _puertas(html, organismo.sitio):
            if puerta in ya_candidatos:
                continue
            html_puerta = _traer(puerta)
            if opciones['espera']:
                time.sleep(opciones['espera'])
            if html_puerta:
                candidatos += _candidatos(html_puerta, puerta)

        # Un solo link por URL (puede repetirse entre páginas), del más
        # prometedor al resto, y hasta el máximo del sitio.
        unicos = {}
        for c in candidatos:
            unicos.setdefault(c['url'], c)
        lista = sorted(unicos.values(), key=lambda c: -c['puntaje'])
        candidatos = lista[:opciones['max_por_sitio']]

        creados = omitidos = 0
        for candidato in candidatos:
            try:
                if self._ya_cargado(candidato, organismo):
                    omitidos += 1
                    continue
                if self._crear_tramite(candidato, organismo, opciones):
                    creados += 1
            except Exception as error:
                # Un link tonto no puede frenar la corrida entera: se
                # anota y se sigue con el siguiente.
                self.stderr.write(self.style.WARNING(
                    f'  ! {organismo.nombre}: no se pudo cargar '
                    f'«{candidato["texto"][:60]}» ({error})'
                ))
        return creados, omitidos

    @staticmethod
    def _ya_cargado(candidato, organismo):
        """Misma URL o mismo título del mismo organismo: no duplicar."""
        return Tramite.objects.filter(
            enlace_oficial=candidato['url']
        ).exists() or Tramite.objects.filter(
            titulo=_titulo_limpio(candidato['texto'], candidato['url']),
            organismo=organismo,
        ).exists()

    def _crear_tramite(self, candidato, organismo, opciones):
        """Entra a la página del link y arma el trámite con sus requisitos."""
        pagina = _traer(candidato['url'])
        if opciones['espera']:
            time.sleep(opciones['espera'])

        if pagina:
            sopa = BeautifulSoup(pagina, 'html.parser')
            descripcion = _descripcion(sopa, organismo.nombre)
            requisitos = _requisitos(sopa)
        else:
            descripcion = f'Trámite informado por {organismo.nombre}.'
            requisitos = []

        titulo = _titulo_limpio(candidato['texto'], candidato['url'])
        contexto = (
            f'{organismo.nombre} {organismo.ocupacion} '
            f'{candidato["texto"]} {candidato["url"]}'
        )
        with transaction.atomic():
            tramite = Tramite.objects.create(
                titulo=titulo,
                tema=_tema_para(contexto),
                modalidad=_modalidad_para(contexto),
                municipio=_municipio_para(organismo.nombre),
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
