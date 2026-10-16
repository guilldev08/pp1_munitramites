"""Todas las palabras del scraper, en un solo lugar.

Si el scraper «toma de más» o «toma de menos», se corrige acá y no en la
lógica. Las listas que importan:

    · PALABRAS_FUERTES   una sola ya huele a trámite (dni, licencia…).
    · PALABRAS_DEBILES   ambiguas: suman, pero no alcanzan solas.
    · PALABRAS_RUIDO     caminos que nunca son un trámite (noticias, PDF…).
    · PALABRAS_PUERTA    entradas al portal de trámites del sitio.
    · PALABRAS_REQUISITO frases de «qué hay que presentar».
    · PALABRAS_CASCARA   texto de menú/pie que se cuela como dato.
    · PALABRAS_RELLENO   descripciones que son la bajada del sitio.
    · TITULOS_GENERICOS  rótulos de botón o de sección, no de trámite.
    · PALABRAS_TURNO     links para pedir turno.
    · TEMAS_POR_PALABRA  los 7 temas del catálogo, por palabra.
"""

# --- Qué link parece un trámite --------------------------------------
# Fuerte: alcanza con una para seguir el link (ver relevancia.py).
PALABRAS_FUERTES = (
    'tramite', 'dni', 'pasaporte', 'partida', 'nacimiento', 'defuncion',
    'matrimonio', 'licencia', 'conducir', 'catastro', 'habilitacion',
    'antecedente', 'monotributo', 'jubilacion', 'pension', 'subsidio',
    'beca', 'discapacidad', 'vacuna', 'padron', 'libreta', 'carnet',
    'cedula', 'escritura', 'dominio', 'patente', 'vialidad', 'cud',
    'registro civil', 'estado civil', 'asignacion',
)

# Débil: ambigua. Suma, pero sola no alcanza (dos débiles = un fuerte).
PALABRAS_DEBILES = (
    'certificado', 'constancia', 'registro', 'inscripcion', 'turno',
    'impuesto', 'tasa', 'factura', 'contribucion', 'comercio', 'personas',
    'vivienda', 'lote', 'alquiler', 'empleo', 'domicilio', 'carne',
    'formulario', 'solicitud', 'renovacion', 'servicio', 'gestion',
)

# Caminos que nunca son un trámite: noticias, categorías y compañía.
PALABRAS_RUIDO = (
    '/noticia', '/noticias', '/novedad', '/nota', '/prensa', '/agenda',
    '/evento', '/category/', '/categoria/', '/blog', '/tag/', '/wp-',
    '/feed', '/rss', '/contacto', '/privacidad', '/terminos',
    '/quienes-somos', '/institucional', '/autoridades', '/organigrama',
    '/galeria', '/audiovisual', '/multimedia', '/transparencia',
    '/licitacion', '/concurso', '/boletin', '/mapa-del-sitio',
    '/buscar', '/login', '/ingresar', '/mi-cuenta', '/carrito',
    # Un «tema» es un listado de servicios, no la ficha de uno.
    '/tema/',
    '.pdf', '.doc', '.xls', '.jpg', '.jpeg', '.png', '.gif', '.mp4',
    '.zip',
)

# Redes sociales: enlaces con URL rara pero sin texto.
REDES = (
    'facebook.com', 'instagram.com', 'youtube.com', 'twitter.com',
    '://x.com/', 'linkedin', 'tiktok', 'whatsapp', 'wa.me', 'telegram',
)

# --- Puertas: portales de trámites del sitio -------------------------
# Los portales esconden los trámites detrás de una página de entrada
# («Servicios», «Portal del Ciudadano», «Turnos»…). Si el sitio tiene
# una, se scrapea también.
PALABRAS_PUERTA = (
    'ciudadano', 'servicio', 'tramite', 'online', 'on-line', 'turno',
    'gestion', 'mesa de entradas',
)

# --- Requisitos: frases de «qué hay que presentar» -------------------
PALABRAS_REQUISITO = (
    'dni', 'documento', 'original', 'copia', 'formulario', 'presentar',
    'acreditar', 'abonar', 'acompanar', 'vigente', 'certificado',
    'partida', 'constancia', 'comprobante', 'foto', 'fotocopia', 'turno',
)

# --- Cáscara: texto de menú/pie que nunca es dato --------------------
# Los portales envuelven los links de menú en bloques enormes: si un
# título o un requisito trae esto, es el menú colado y se descarta.
PALABRAS_CASCARA = (
    'ver mas', 'leer mas', 'seguir leyendo', 'mas informacion',
    'compartir', 'imprimir', 'multimedia', 'galeria', 'redes sociales',
    'suscrib', 'newsletter', 'mapa del sitio', 'politica de privacidad',
    'terminos y condiciones', 'todos los derechos', 'inicio', 'contacto',
    'tramites y gestiones', 'informacion general',
    'exenciones y bonificaciones', 'boletin oficial', 'menu',
)

# --- Relleno: descripciones que son la bajada del sitio ---------------
PALABRAS_RELLENO = (
    'sitio de la', 'sitio oficial', 'portal oficial', 'pagina oficial',
    'todos los derechos', 'politica de privacidad', 'uso de cookies',
    'mapa del sitio', 'suscribite', 'seguinos', 'facebook', 'instagram',
)

# --- Títulos genéricos: son un botón o una sección, no un trámite -----
TITULOS_GENERICOS = (
    'tramites', 'tramites y gestiones', 'gestiones', 'servicios',
    'servicios al ciudadano', 'inicio', 'home', 'principal',
    'gestionar los servicios', 'mas informacion', 'ver mas', 'leer mas',
    'ingresar', 'acceder', 'consultas', 'contacto', 'informacion general',
    'novedades', 'noticias', 'servicios on line',
)

# Palabras de sección: un rótulo con DOS o más es un volcado de menú
# («Inmobiliario Trámites y Gestiones Información General…»), no un
# nombre de trámite.
PALABRAS_SECCION = (
    'tramites', 'gestiones', 'servicios', 'informacion', 'general',
    'exenciones', 'bonificaciones', 'estados', 'consideraciones',
    'multimedia', 'galeria', 'novedades', 'noticias', 'inicio',
    'contacto', 'consultas', 'institucional', 'autoridades',
)

# --- Turnos: links para pedir turno en la ficha ----------------------
PALABRAS_TURNO = (
    'turno', 'reserv', 'sacar cita', 'pedir cita', 'cita previa',
)

# --- Clasificación: los 7 temas del catálogo -------------------------
# Los mismos que carga cargar_datos.py, en el orden en que se los
# prueba: gana el primero que calce.
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
