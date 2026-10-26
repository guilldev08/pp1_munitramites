# -*- coding: utf-8 -*-
"""Dataset curado de tramites oficiales de Misiones.

Los datos salen de las paginas y PDFs oficiales relevados en octubre de 2026.
No se completan requisitos por inferencia: cada lista refleja lo publicado por
el organismo. Las fuentes de cada ficha se guardan en ``fuentes`` para generar
el CSV de trazabilidad.
"""

MUNICIPIOS = ['Posadas', 'Oberá', 'Puerto Iguazú', 'Eldorado']

TEMAS = [
    'Documentación',
    'Tránsito',
    'Comercio',
    'Seguridad',
    'Salud',
    'Impuestos',
    'Vivienda',
    'Obras y Catastro',
    'Servicios Públicos',
    'Ambiente',
]

ORGANISMOS = {
    'Registro Provincial de las Personas': {
        'direccion': 'Chacra 32-33, Posadas, Misiones',
        'ocupacion': 'Identidad, estado civil y actas',
        'sitio': 'https://www.registrocivil.misiones.gov.ar/',
    },
    'Municipalidad de Posadas': {
        'direccion': 'San Martín 1579, Posadas, Misiones',
        'ocupacion': 'Trámites y servicios municipales',
        'sitio': 'https://posadas.gob.ar/',
    },
    'Administración Tributaria de Misiones (ATM)': {
        'direccion': 'San Martín 1754, Posadas, Misiones',
        'ocupacion': 'Impuestos provinciales y recaudación',
        'sitio': 'https://atmisiones.gob.ar/',
    },
    'Instituto Provincial de Desarrollo Habitacional (IPRODHA)': {
        'direccion': 'Av. Roque Pérez 1743, Posadas, Misiones',
        'ocupacion': 'Vivienda social y regularización dominial',
        'sitio': 'https://iprodha.misiones.gob.ar/',
    },
    'Energía de Misiones S.A.': {
        'direccion': 'La Rioja 2051, Posadas, Misiones',
        'ocupacion': 'Servicio eléctrico provincial',
        'sitio': 'https://www.energiademisiones.com.ar/',
    },
    'SAMSA - Aguas de Misiones S.A.': {
        'direccion': 'Av. López y Planes 2577, Posadas, Misiones',
        'ocupacion': 'Agua potable y cloacas',
        'sitio': 'https://samsa.com.ar/',
    },
    'Ministerio de Salud Pública de Misiones': {
        'direccion': 'Av. Lavalle 5377 y Av. Andresito, Posadas, Misiones',
        'ocupacion': 'Saneamiento ambiental y habilitaciones sanitarias',
        'sitio': 'https://salud.misiones.gob.ar/',
    },
    'Policía de Misiones': {
        'direccion': 'Félix de Azara 2481, Posadas, Misiones',
        'ocupacion': 'Certificados y trámites policiales',
        'sitio': 'https://policiamisiones.gob.ar/',
    },
    'Dirección General de Personas Jurídicas y Registro Público': {
        'direccion': 'Av. Roque Pérez 2398, 2° piso, Posadas, Misiones',
        'ocupacion': 'Sociedades, entidades civiles y registro público',
        'sitio': 'https://personasjuridicas.misiones.gob.ar/',
    },
    'Municipalidad de Oberá': {
        'direccion': 'Jujuy 58, Oberá, Misiones',
        'ocupacion': 'Trámites y servicios municipales',
        'sitio': 'https://www.obera.gob.ar/',
    },
    'Municipalidad de Puerto Iguazú': {
        'direccion': 'Av. Tres Fronteras 122, Puerto Iguazú, Misiones',
        'ocupacion': 'Trámites y servicios municipales',
        'sitio': 'https://www.iguazu.gob.ar/',
    },
}

RC = 'Registro Provincial de las Personas'
RC_URL = 'https://www.registrocivil.misiones.gov.ar/index.php/guia-de-tramites/'
POSADAS = 'Municipalidad de Posadas'
POSADAS_URL = 'https://posadas.gob.ar/guiatramite'
POSADAS_AJAX = 'https://posadas.gob.ar/ajaxGuiatramiteDatos'
ATM = 'Administración Tributaria de Misiones (ATM)'
IPRODHA = 'Instituto Provincial de Desarrollo Habitacional (IPRODHA)'
ENERGIA = 'Energía de Misiones S.A.'
SAMSA = 'SAMSA - Aguas de Misiones S.A.'
SALUD = 'Ministerio de Salud Pública de Misiones'
POLICIA = 'Policía de Misiones'
PJ = 'Dirección General de Personas Jurídicas y Registro Público'
OBERA = 'Municipalidad de Oberá'
IGUAZU = 'Municipalidad de Puerto Iguazú'

SEDES = {
    'rc_central': [
        ('Sede Central del Registro Civil', 'Posadas', 'Chacra 32-33, Posadas, Misiones'),
    ],
    'rc': [
        ('Sede Central del Registro Civil', 'Posadas', 'Chacra 32-33, Posadas, Misiones'),
        ('Delegación CAV', 'Posadas', 'Av. Urquiza y Av. San Martín, Posadas, Misiones'),
        ('Delegación Oberá', 'Oberá', 'Av. Libertad 755, Oberá, Misiones'),
        ('Delegación Eldorado', 'Eldorado', 'Km 9, Calle Cuyo 230, Eldorado, Misiones'),
        ('Delegación Puerto Iguazú', 'Puerto Iguazú', 'Calle 1° de Mayo 346, B° Villa Florida, Puerto Iguazú, Misiones'),
    ],
    'rc_matrimonio': [
        ('Sede Central del Registro Civil', 'Posadas', 'Chacra 32-33, Posadas, Misiones'),
        ('Sala Única de Matrimonios', 'Posadas', 'Centro Cultural La Estación, Cuarto Tramo Av. Costanera, Posadas, Misiones'),
        ('Delegación CAV', 'Posadas', 'Av. Urquiza y Av. San Martín, Posadas, Misiones'),
        ('Delegación Oberá', 'Oberá', 'Av. Libertad 755, Oberá, Misiones'),
        ('Delegación Eldorado', 'Eldorado', 'Km 9, Calle Cuyo 230, Eldorado, Misiones'),
        ('Delegación Puerto Iguazú', 'Puerto Iguazú', 'Calle 1° de Mayo 346, B° Villa Florida, Puerto Iguazú, Misiones'),
    ],
    'rc_defuncion': [
        ('Centralizadora de Defunciones', 'Posadas', 'CAV, Av. Urquiza y Av. San Martín, Posadas, Misiones'),
    ],
    'posadas_obras': [
        ('Palacio Municipal - Obras Privadas', 'Posadas', 'San Martín 1579, 1er piso, Posadas, Misiones'),
    ],
    'posadas_automotores': [
        ('Palacio Municipal - Dirección de Automotores', 'Posadas', 'San Martín 1579, 3er piso, Posadas, Misiones'),
    ],
    'posadas_comercio': [
        ('Palacio Municipal - Mesa de Entradas', 'Posadas', 'San Martín 1579, Posadas, Misiones'),
    ],
    'posadas_licencias': [
        ('CAV Hiper', 'Posadas', 'Paseo Libertad, planta baja, Posadas, Misiones'),
        ('CAV San Martín', 'Posadas', 'Av. Urquiza y Av. San Martín, Posadas, Misiones'),
    ],
    'posadas_agentes': [
        ('CAV Dolores Norte', 'Posadas', 'Av. Pueyrredón 3858, Posadas, Misiones'),
    ],
    'posadas_servicios': [
        ('Palacio Municipal - Inspección General', 'Posadas', 'San Martín 1579, subsuelo, Posadas, Misiones'),
    ],
    'atm': [
        ('Sede Central de ATM', 'Posadas', 'San Martín 1754, Posadas, Misiones'),
    ],
    'iprodha': [
        ('Sede Central de IPRODHA', 'Posadas', 'Av. Roque Pérez 1743, Posadas, Misiones'),
    ],
    'energia': [
        ('Sede Central de Energía de Misiones', 'Posadas', 'La Rioja 2051, Posadas, Misiones'),
    ],
    'energia_electro': [
        ('Gerencia de Responsabilidad Social Empresaria', 'Posadas', 'Ayacucho 2051, Posadas, Misiones'),
    ],
    'samsa': [
        ('Oficinas de SAMSA', 'Posadas', 'Av. López y Planes 2577, Posadas, Misiones'),
    ],
    'salud': [
        ('Dirección de Saneamiento Ambiental', 'Posadas', 'Av. Lavalle 5377 y Av. Andresito, Posadas, Misiones'),
    ],
    'policia': [
        ('Jefatura de Policía de Misiones', 'Posadas', 'Félix de Azara 2481, Posadas, Misiones'),
        ('Unidad Regional I', 'Posadas', 'Félix de Azara y Córdoba, Posadas, Misiones'),
    ],
    'pj': [
        ('Dirección General de Personas Jurídicas', 'Posadas', 'Av. Roque Pérez 2398, 2° piso, Posadas, Misiones'),
    ],
    'obera': [
        ('Palacio Municipal de Oberá', 'Oberá', 'Jujuy 58, Oberá, Misiones'),
    ],
    'obera_carnet': [
        ('Oficina de Seguridad Alimentaria', 'Oberá', 'Bolivia 530, Oberá, Misiones'),
    ],
    'obera_castracion': [
        ('Departamento de Zoonosis y Salud Animal', 'Oberá', 'A. José Ingenieros 1400, Oberá, Misiones'),
    ],
    'iguazu': [
        ('Palacio Municipal de Puerto Iguazú', 'Puerto Iguazú', 'Av. Tres Fronteras 122, Puerto Iguazú, Misiones'),
    ],
}


def _ficha(titulo, tema, modalidad, municipio, organismo, descripcion,
           requisitos, enlaces, fuentes, sedes, destacado=False):
    return {
        'titulo': titulo,
        'tema': tema,
        'modalidad': modalidad,
        'municipio': municipio,
        'organismo': organismo,
        'descripcion': descripcion,
        'requisitos': list(requisitos),
        'enlaces': list(enlaces),
        'fuentes': list(fuentes),
        'sedes': list(sedes),
        'destacado': destacado,
    }


def rc(titulo, descripcion, requisitos, slug, *, modalidad='presencial',
       sedes='rc', tema='Documentación', fuentes=(), destacado=False,
       enlace='Guía oficial del trámite'):
    url = RC_URL + slug
    return _ficha(
        titulo, tema, modalidad, 'Posadas', RC, descripcion, requisitos,
        [(enlace, url)],
        [(url, 'Título, descripción y requisitos del trámite')] + list(fuentes),
        SEDES[sedes], destacado,
    )


def posadas(titulo, descripcion, requisitos, idtramite, *, tema,
            modalidad='presencial', sedes='posadas_comercio', fuentes=(),
            destacado=False):
    return _ficha(
        titulo, tema, modalidad, 'Posadas', POSADAS, descripcion, requisitos,
        [('Guía de trámites de Posadas', POSADAS_URL)],
        [
            (POSADAS_URL, 'Índice de la Guía de Trámites municipal'),
            (POSADAS_AJAX, f'Ficha idtramite={idtramite}: título, descripción, requisitos y sede'),
        ] + list(fuentes),
        SEDES[sedes], destacado,
    )


TRAMITES = []

# ---------------------------------------------------------------------------
# Registro Provincial de las Personas
# ---------------------------------------------------------------------------

TRAMITES.extend([
    rc(
        'Nuevo ejemplar de DNI',
        'Solicitud de un nuevo ejemplar del Documento Nacional de Identidad en cualquier delegación del Registro Provincial de las Personas.',
        [
            'Abonar la tasa de $10.000.',
            'Los menores de edad nacidos en Misiones no necesitan presentar acta de nacimiento.',
            'El DNI llega al domicilio informado en 15 días hábiles aproximadamente.',
            'Si el correo no encuentra a nadie, el DNI se retira en la delegación donde se hizo el trámite.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Cambio de domicilio en el DNI',
        'Actualiza la dirección que figura en el DNI y define el domicilio donde se recibirá el nuevo ejemplar.',
        [
            'Informar la dirección exacta que se consignará en el DNI.',
            'Abonar la tasa de $10.000.',
            'Los menores de edad nacidos en Misiones no necesitan presentar acta de nacimiento.',
            'El DNI llega al domicilio informado en 15 días hábiles aproximadamente.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'DNI Exprés',
        'Emisión acelerada del DNI, con entrega estimada en 96 horas hábiles.',
        [
            'Presentar el último ejemplar del DNI.',
            'Abonar $26.000 con débito, crédito o billetera virtual.',
            'El DNI llega al domicilio informado o queda en la delegación si el correo no lo entrega.',
        ],
        'tramites-de-dni',
        destacado=True,
    ),
    rc(
        'DNI Cero Año',
        'Emisión gratuita del DNI para un recién nacido, en la localidad donde nació.',
        [
            'Presentar el acta de nacimiento.',
            'Realizar la inscripción del nacimiento en la localidad donde nació el bebé.',
            'El DNI no tiene costo.',
            'Entrega estimada: 15 días hábiles.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Actualización de DNI de 5 a 8 años',
        'Actualización del DNI de los chicos que tienen entre 5 y 8 años.',
        [
            'Padre, madre o tutor presente con DNI en mano.',
            'El menor debe estar presente.',
            'Presentar el DNI del menor.',
            'Los menores nacidos en Misiones no necesitan presentar acta de nacimiento.',
            'Abonar la tasa de $10.000.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Actualización de DNI a los 14 años',
        'Actualización obligatoria del DNI al cumplir 14 años.',
        [
            'El menor debe estar presente y puede realizar el trámite solo.',
            'Presentar el DNI.',
            'Abonar la tasa de $10.000.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Actualización de DNI para mayores de 18 años',
        'Actualización del DNI para personas adultas que deben acreditar identidad y datos filiatorios.',
        [
            'Presentar el DNI en mano.',
            'Presentar el acta de nacimiento.',
            'Presentar el DNI de uno de los padres o de dos testigos argentinos, mayores de 18 años y al menos 5 años mayores.',
            'Completar el Formulario de Información Sumaria.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'DNI para personas extranjeras',
        'Nuevo ejemplar, primera identificación para ciudadanos del MERCOSUR y actualización de DNI para personas extranjeras.',
        [
            'Acreditar residencia temporaria o permanente vigente, según el caso.',
            'Presentar el DNI anterior, si ya posee uno.',
            'Abonar $20.000 por nuevo ejemplar, primera identificación o actualización.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Reposición de DNI por dato incorrecto',
        'Corrección de un dato incorrecto consignado en el DNI mediante la emisión de un nuevo ejemplar.',
        [
            'Presentarse con el DNI que contiene el error.',
            'Presentar el acta de nacimiento.',
            'Abonar el arancel correspondiente.',
            'El DNI se inutiliza y el nuevo ejemplar llega en 15 días hábiles aproximadamente.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Rectificación de DNI por acta modificada',
        'Emisión de un nuevo DNI cuando se modificó un dato del acta de nacimiento que impacta en el documento.',
        [
            'Presentarse con el DNI que posee el error.',
            'Presentar el acta de nacimiento debidamente rectificada.',
            'Abonar $3.000 en efectivo en la delegación.',
        ],
        'tramites-de-dni',
    ),
    rc(
        'Pasaporte para mayores de edad',
        'Emisión del pasaporte argentino para personas mayores de edad.',
        [
            'Presentarse con el último DNI.',
            'Ser argentino.',
            'Abonar $100.000.',
            'El pasaporte llega al domicilio en 15 días hábiles aproximadamente.',
        ],
        'tramites-de-pasaporte',
        destacado=True,
    ),
    rc(
        'Pasaporte para menores de edad',
        'Emisión del pasaporte argentino para menores de edad, con presencia del menor y documentación de sus padres.',
        [
            'El menor debe estar presente con el último DNI.',
            'Ser argentino.',
            'Presentar la partida de nacimiento del menor.',
            'Presentar el documento del padre o la madre.',
            'Abonar $100.000.',
        ],
        'tramites-de-pasaporte',
    ),
    rc(
        'Pasaporte Exprés',
        'Emisión acelerada del pasaporte, con entrega estimada en 72 a 96 horas hábiles.',
        [
            'Presentarse con el último DNI.',
            'Ser argentino.',
            'Para pasaporte de menor: presentar la partida de nacimiento del menor.',
            'Abonar $200.000.',
        ],
        'tramites-de-pasaporte',
    ),
    rc(
        'Inscripción de nacimiento dentro de los 40 días',
        'Inscripción del recién nacido en el Registro Civil, dentro de los 40 días posteriores al nacimiento.',
        [
            'Presentar el certificado médico del nacimiento.',
            'Madre y padre con DNI.',
            'Realizar la inscripción únicamente en la localidad donde nació el bebé.',
        ],
        'nacimientos',
        destacado=True,
    ),
    rc(
        'Inscripción de nacimiento de 14 a 18 años',
        'Inscripción de nacimiento de personas mayores de 14 y hasta 18 años inclusive.',
        [
            'Presentar certificado de edad presuntiva.',
            'Presentar 2 testigos argentinos mayores de edad.',
            'Puede realizarse en cualquier delegación cercana al domicilio.',
        ],
        'nacimientos',
    ),
    rc(
        'Reconocimiento de hijo o hija',
        'Reconocimiento filial de un hijo o hija menor de edad ante el Registro Civil.',
        [
            'Presentarse ambos padres con sus DNI.',
            'El menor debe presentarse con DNI y acta de nacimiento.',
            'Si se presenta solo el padre: 2 testigos mayores de edad que no sean familiares.',
            'Abonar el arancel correspondiente con unificación de actas.',
        ],
        'nacimientos',
    ),
    rc(
        'Adición de apellido materno',
        'Incorporación del apellido de la madre en el acta de nacimiento y en el DNI.',
        [
            'Presentar el acta de nacimiento del menor.',
            'Presentar el acta de nacimiento de la madre.',
            'Presentar el DNI del menor y fotocopia del DNI de la madre.',
            'Menores de 13 años: madre y padre presentes. De 13 a 17 años: madre presente.',
            'Abonar la tasa correspondiente y tramitar un nuevo DNI.',
        ],
        'nacimientos',
    ),
    rc(
        'Inscripción de matrimonio',
        'Inscripción y celebración del matrimonio civil en la jurisdicción donde uno de los contrayentes tiene domicilio.',
        [
            'Fotocopia de ambos DNI.',
            'Datos personales de ambos contrayentes: edad, nacionalidad, domicilio, lugar de nacimiento y profesión.',
            'Uno de los cónyuges debe poseer domicilio en la jurisdicción donde se celebrará el matrimonio.',
            'Fotocopia del acta de nacimiento de los hijos en común, si los hay.',
            'Datos de los padres de ambos contrayentes.',
            '2 testigos mayores de 18 años con fotocopia de DNI; 4 testigos si se celebra fuera de la oficina.',
            'Acta de matrimonio anterior con marginal de divorcio o acta de defunción, según corresponda.',
            'Presentar libreta de matrimonio civil y abonar las tasas respectivas.',
            'Presentar actas de nacimiento de los contrayentes, si las poseen.',
            'Menores de 16 años: dispensa de edad judicial. Menores de 18: DNI de los padres y presencia el día de la ceremonia.',
        ],
        'matrimonios',
        destacado=True,
    ),
    rc(
        'Matrimonio de extranjeros no residentes',
        'Celebración de matrimonio entre extranjeros no residentes en la provincia de Misiones, con turno previo.',
        [
            'Completar el Formulario de Declaración Jurada de Matrimonio y firmarlo en original.',
            'Fotocopia certificada notarialmente del pasaporte o documento migratorio y constancia de ingreso al país.',
            'Acta notarial ante escribano público matriculado en Misiones con el domicilio de referencia y el plazo de estadía.',
            'Testigos: 2 si se celebra en la oficina y 4 en puntos turísticos.',
            'Abonar la tasa administrativa.',
            'Divorciados: acta de matrimonio con marginal de divorcio legalizada y apostillada con traducción.',
            'Viudos: acta de defunción y acta de matrimonio legalizadas y apostilladas.',
            'Solicitar turno por correo y presentar los originales 5 días antes del enlace.',
        ],
        'matrimonios-extranjeros',
        sedes='rc_matrimonio',
    ),
    rc(
        'Unión convivencial',
        'Registración de la unión convivencial de dos personas que comparten domicilio y cumplen los requisitos legales.',
        [
            '2 testigos mayores de edad con fotocopia de DNI, que no pueden ser familiares.',
            'DNI de ambos contrayentes con el mismo domicilio; sirve constancia de trámite.',
            'Estado civil soltero, viudo o divorciado; sin matrimonio ni unión convivencial vigente.',
            'Actas de nacimiento de los contrayentes, original y copia.',
            'Abonar la tasa de $17.100.',
            'Imprimir y presentar el formulario.',
        ],
        'union-convivencial',
        sedes='rc_matrimonio',
    ),
    rc(
        'Cese de unión convivencial',
        'Registración del cese de una unión convivencial inscripta en el Registro Civil.',
        [
            'Completar el Formulario de Cese de Unión Convivencial.',
            'Presencia de ambos convivientes.',
            'Abonar la tasa de $17.100.',
        ],
        'union-convivencial',
        sedes='rc_central',
    ),
    rc(
        'Inscripción de defunción',
        'Inscripción del fallecimiento en la Centralizadora de Defunciones del Registro Civil.',
        [
            'Presentar el certificado médico expedido por el médico.',
            'Presentar el DNI físico del fallecido.',
            'Presentar fotocopia del DNI que se presenta.',
            'Realizar la inscripción dentro de los 2 días hábiles.',
            'Si se excede el plazo, solicitar la inscripción fuera de término conforme al Art. 60 de la Ley 26.413.',
        ],
        'defunciones',
        sedes='rc_defuncion',
    ),
    rc(
        'Inscripción de divorcio',
        'Inscripción de una sentencia de divorcio en el Registro Civil.',
        [
            'Presentar el oficio judicial o testimonio original.',
            'Si se presenta desde otra provincia por correo, el documento debe tener firma digital.',
            'Abonar $20.700.',
            'El trámite tarda aproximadamente 5 días hábiles.',
        ],
        'divorcio',
        modalidad='mixta',
    ),
    rc(
        'Solicitud de actas legalizadas',
        'Solicitud en línea de actas de nacimiento, matrimonio o defunción legalizadas de la provincia de Misiones.',
        [
            'Abonar $3.200 por cada acta y conservar el número de comprobante de HELIPAGOS o MACROCLICK.',
            'Ingresar el DNI de la persona que solicita el acta.',
            'Completar tipo de acta, nombre, fecha, localidad y año; número, tomo y folio si se conocen.',
            'Si solicita un tercero, adjuntar autorización del titular con firma certificada por juzgado o escribano.',
            'Para acta de defunción, adjuntar foto del DNI del solicitante en el campo de autorización.',
            'Sólo se emiten actas de la provincia de Misiones.',
        ],
        'solicitud-de-actas',
        modalidad='virtual',
        destacado=True,
    ),
    rc(
        'Rectificación de actas de estado civil',
        'Corrección de errores en actas de nacimiento, matrimonio o defunción.',
        [
            'Presentar el acta que se quiere rectificar.',
            'Presentar el DNI del titular del acta.',
            'Completar el Formulario de Rectificaciones, si corresponde.',
            'Si el error está en el nombre o DNI de padre o madre: presentar el acta de nacimiento de esa persona.',
            'Abonar la tasa correspondiente.',
            'Iniciar en cualquier delegación o por mail a centralrectificacionesrpp@gmail.com.',
        ],
        'rectificacion-de-actas',
        modalidad='mixta',
    ),
    rc(
        'Legalización de título',
        'Legalización de títulos educativos originales de la provincia de Misiones.',
        [
            'Presentar el título original en formato papel; no se legalizan fotocopias.',
            'Sólo se legalizan títulos de la provincia de Misiones.',
            'Abonar $8.200 por hoja.',
            'Puede presentarlo el titular u otra persona sin autorización.',
            'Títulos digitales: usar el ReFE. Para el exterior, enviar el pedido a legalizacionesrpp@gmail.com con el comprobante.',
        ],
        'legalizacion-de-titulo',
        sedes='rc_central',
    ),
    rc(
        'Permiso de viaje para menores dentro del país',
        'Autorización para que un menor viaje dentro del territorio argentino con un adulto o solo, según su edad.',
        [
            'Completar el formulario de autorización con destino, plazos, motivos y datos del acompañante.',
            'Acreditar el vínculo con acta de nacimiento o DNI/pasaporte del menor.',
            'Presentar el DNI del progenitor que autoriza.',
            'Presentar el DNI del acompañante autorizado, si corresponde.',
            'También se puede acreditar el vínculo con libreta de matrimonio con nacimiento asentado o testimonio judicial de adopción.',
            'Abonar $12.500.',
            'Es un trámite personal: debe presentarse la madre, el padre o el representante legal.',
        ],
        'permiso-de-viaje',
        sedes='rc_central',
        destacado=True,
    ),
    rc(
        'Inscripción tardía administrativa de nacimiento',
        'Inscripción de nacimientos fuera de término en sedes administrativas del Registro, sin límite de edad.',
        [
            'Presentar el DNI del solicitante.',
            'Presentar la documentación complementaria que indique la delegación.',
            'El trámite no tiene límite de edad.',
            'Puede iniciarse en cualquier delegación del Registro.',
        ],
        'inscripcion-tardia-administrativa',
    ),
    rc(
        'Inscripción de acta de extraña jurisdicción',
        'Inscripción en Misiones de actas de nacimiento, matrimonio o defunción emitidas en otra jurisdicción.',
        [
            'Presentar el acta correspondiente legalizada por la provincia de origen.',
            'Si es del extranjero, debe estar apostillada y con traducción si está en otro idioma.',
            'Completar el Formulario de Inscripción de Extraña Jurisdicción.',
            'Abonar $4.400.',
            'Presentar en Chacra 32-33 o comunicarse por mail a rppmesadeentrada@gmail.com.',
        ],
        'extrana-jurisdiccion',
        modalidad='mixta',
        sedes='rc_central',
    ),
    rc(
        'Registración de pacto convivencial',
        'Registración de un pacto de convivencia celebrado por instrumento privado con certificación de firmas.',
        [
            'Presentar el instrumento privado con certificación de firmas.',
            'Abonar la tasa de $41.000.',
            'Presentar en mesa de entradas del Registro, Chacra 32-33.',
        ],
        'matrimonios',
        sedes='rc_central',
    ),
    rc(
        'Registración de convención matrimonial',
        'Registración y protocolización de una convención matrimonial otorgada por escritura pública.',
        [
            'Presentar la escritura pública original y copia debidamente certificada por el escribano.',
            'Abonar la tasa de $51.100.',
            'Presentar en mesa de entradas del Registro, Chacra 32-33, primer piso.',
        ],
        'matrimonios',
        sedes='rc_central',
    ),
])

# ---------------------------------------------------------------------------
# Municipalidad de Posadas
# ---------------------------------------------------------------------------

TRAMITES.extend([
    posadas(
        'Inicio de trámite de obra en el sistema GOP',
        'Registro digital de obras privadas para obtener factibilidad, permisos de obra nueva, reforma, ampliación, demolición y final de obra.',
        [
            'Contar con un profesional habilitado para la gestión y el registro de la obra.',
            'Registrar el usuario propio y el del profesional autorizado en el sistema GOP.',
            'Fotocopias de DNI certificadas por escribano o funcionario municipal.',
            'Título de propiedad, boleto o variante que acredite la titularidad.',
            'Constancia de número de finca y certificación de firmas.',
            'Constancia de aprovisionamiento de agua y cloaca.',
            'Constancia de habilitación profesional.',
            'Mensura o acta de amojonamiento y visado de pago del Colegio de Agrimensores.',
            'Plano de arquitectura, relevamiento fotográfico y planos de servicios contra incendio.',
            'Constancia de pago del visado de documentación de servicios contra incendio.',
            'Plano de estructuras portantes y memorias de cálculo.',
            'Plano de instalaciones complementarias.',
            'Para registraciones: Declaración Jurada de las Obras Existentes.',
        ],
        1,
        tema='Obras y Catastro',
        modalidad='virtual',
        sedes='posadas_obras',
        destacado=True,
    ),
    posadas(
        'Certificado final de obra',
        'Certificación municipal de que la obra aprobada se encuentra terminada y en condiciones de ser habilitada.',
        [
            'Planilla para Final de Obra por duplicado con los datos del expediente de construcción aprobado y firmada por el solicitante.',
            'Conjuntos habitacionales: certificación final de infraestructuras y aprobación final de la Dirección de Ingeniería (Ord. N° 102/96).',
            'Planos de instalaciones complementarias aprobadas: electricidad, salubridad y gas, según el caso.',
            'Plano de instalación electromecánica aprobada, si existe.',
            'Certificado de auditoría de gas para instalaciones de GLP.',
            'Verificación de obra existente: planillas por duplicado de Constancia de Obra Terminada firmadas por el profesional.',
            'Declaración Jurada para propiedad horizontal, cuando corresponda.',
            'Constancia de conexión cloacal de SAMSA si existe red habilitada.',
            'Certificado de inspección de instalaciones contra incendio de Bomberos para edificios, locales, clubes y sitios con público.',
        ],
        3,
        tema='Obras y Catastro',
        sedes='posadas_obras',
    ),
    posadas(
        'Cambio de categoría de baldío a edificado',
        'Certificado de construcción existente para pasar un inmueble de la categoría de baldío a edificado.',
        [
            'Presentar copia del plano aprobado.',
            'Presentar final de obra total o parcial, según corresponda.',
        ],
        4,
        tema='Obras y Catastro',
        sedes='posadas_obras',
    ),
    posadas(
        'Ocupación de la vía pública con vallado de obra',
        'Autorización para instalar un vallado de obra sobre la vía pública frente al inmueble en construcción.',
        [
            'Nota dirigida a la Dirección de Obras Privadas con número de expediente, ubicación, propietario, profesional responsable y plazo de ocupación.',
            'Croquis técnico del vallado firmado por el profesional: planta, vista, dimensiones y superficie de ocupación.',
            'El vallado debe cumplir el punto 4.1 del Código de Edificación Municipal.',
            'La documentación se agrega al expediente de obra indicado en la nota.',
        ],
        5,
        tema='Obras y Catastro',
        sedes='posadas_obras',
    ),
    posadas(
        'Certificación para inicio de comodato precario',
        'Certificado municipal para iniciar el trámite de comodato precario de un inmueble.',
        [
            'Formulario de Solicitud de Inspección con los datos catastrales del inmueble o datos que permitan su ubicación.',
            'Certificado de domicilio expedido por la Policía de la Provincia.',
            'Abonar el cobro del certificado.',
        ],
        7,
        tema='Obras y Catastro',
        sedes='posadas_obras',
    ),
    posadas(
        'Plan Mejor Vivir',
        'Presentación de refacciones o ampliaciones de viviendas existentes financiadas por IPRODHA, con aval del instituto.',
        [
            'Carpeta Especial con Nota Aclaratoria de presentación para cumplir los requerimientos del Plan Mejor Vivir.',
            'Listado de beneficiarios visado por IPRODHA con el titular de la carpeta.',
            'Planta, vista y corte de lo ejecutado, original y copias, aclarando los rubros en que se actuó.',
            'Abonar el ítem especial con monto fijo previsto en la Resolución N° 77/04.',
        ],
        8,
        tema='Vivienda',
        sedes='posadas_obras',
    ),
    posadas(
        'Visado de expediente de mensura',
        'Visado municipal del expediente de mensura para propiedad horizontal, fraccionamiento simple o fraccionamiento simple especial.',
        [
            'Presentar el expediente de mensura y el plano aprobado que obra en el Archivo de Obras Públicas.',
            'Contar con el final de obra otorgado por la Dirección de Obras Privadas.',
            'Para propiedad horizontal, los planos deben coincidir con la inspección y no presentar situaciones antirreglamentarias.',
            'Para fraccionamiento simple, el planteo debe encuadrarse en la Ordenanza de Fraccionamiento.',
            'Las observaciones se informan a la Dirección de Catastro para su gestión.',
        ],
        9,
        tema='Obras y Catastro',
        sedes='posadas_obras',
    ),
    posadas(
        'Certificado de libre deuda del automotor',
        'Certificado municipal que acredita que el vehículo no registra deudas de patente ni multas vigentes.',
        [
            'Tener el impuesto automotor pago al día.',
            'Presentar un informe de multas vigente emitido por el Tribunal Municipal de Faltas.',
        ],
        16,
        tema='Impuestos',
        sedes='posadas_automotores',
    ),
    posadas(
        'Plan de pagos del automotor',
        'Solicitud de un plan de pagos para regularizar deudas del impuesto automotor municipal.',
        [
            'DNI del titular registral del dominio.',
            'Boleta de servicio del vehículo.',
            'Formulario SR-388 impreso, Certificación de domicilio fiscal electrónico.',
        ],
        16,
        tema='Impuestos',
        sedes='posadas_automotores',
    ),
    posadas(
        'Denuncia de venta del automotor',
        'Comunicación municipal de la venta de un vehículo para deslindar responsabilidades sobre el rodado.',
        [
            'Formulario de denuncia de venta o constancia online.',
            'Recibo con código de verificación emitido por la Dirección Nacional del Registro del Parque Automotor.',
        ],
        16,
        tema='Tránsito',
        sedes='posadas_automotores',
    ),
    posadas(
        'Alta municipal de rodados usados',
        'Alta municipal de un vehículo usado para el pago del impuesto automotor en Posadas.',
        [
            'Título original, constancia de asignación de título o informe histórico de titularidad del Registro Nacional del Parque Automotor.',
            'Certificado de libre deuda y baja del municipio de origen.',
            'DNI del contribuyente.',
        ],
        16,
        tema='Tránsito',
        sedes='posadas_automotores',
    ),
    posadas(
        'Alta municipal de rodados 0 km',
        'Alta municipal de un vehículo nuevo para el pago del impuesto automotor en Posadas.',
        [
            'Título original o constancia de asignación de título del Registro Nacional del Parque Automotor.',
            'Factura de compra original.',
            'DNI del contribuyente.',
        ],
        16,
        tema='Tránsito',
        sedes='posadas_automotores',
    ),
    posadas(
        'Certificado de baja del automotor por cambio de radicación',
        'Baja municipal del vehículo para radicarlo en otra jurisdicción.',
        [
            'Título original o informe histórico de titularidad del Registro Nacional del Parque Automotor.',
            'Tener el impuesto pago al día si la transferencia se hace dentro de Misiones.',
            'Si el vehículo se radica fuera de la provincia, abonar el total del año fiscal en curso.',
            'Presentar informe de multas vigente del Tribunal Municipal de Faltas.',
        ],
        16,
        tema='Tránsito',
        sedes='posadas_automotores',
    ),
    posadas(
        'Inscripción como agente de retención y percepción del DIRySC',
        'Inscripción de contribuyentes que superaron los $600.000.000 de ingresos brutos en el régimen de retención y percepción del DIRySC.',
        [
            'Formulario de solicitud de inscripción como agente.',
            'Formulario DJ-01A.',
            'Copia del DNI de quien suscribe el formulario.',
            'Documentación que acredite representación o personería: poder, acta de designación de autoridades o similar.',
            'Constancia de inscripción en AFIP.',
            'Constancia de inscripción en DGR Misiones o en Convenio Multilateral (Padrón Web con clave fiscal).',
            'Inscribirse dentro de los 15 días del mes siguiente a haber superado el monto mínimo.',
        ],
        20,
        tema='Impuestos',
        sedes='posadas_agentes',
    ),
    posadas(
        'Exclusión del régimen de retención y percepción del DIRySC',
        'Solicitud de exclusión del régimen de retención y percepción del derecho de inspección, registro y servicio de contralor.',
        [
            'Formulario de Solicitud de Certificado de No Retención y/o Percepción Provisorio.',
            'Detalle de las percepciones y retenciones sufridas.',
            'Copia del DNI del firmante.',
            'Documentación que acredite representación o personería.',
            'Constancia de inscripción en AFIP.',
            'Constancia de inscripción en DGR Misiones o en Convenio Multilateral.',
            'Profesionales liberales: título universitario y matrícula.',
        ],
        20,
        tema='Impuestos',
        sedes='posadas_agentes',
    ),
    posadas(
        'Exclusión del DIRySC por saldos a favor',
        'Exclusión total o parcial del régimen cuando su aplicación genera saldos a favor permanentes en el contribuyente.',
        [
            'Nota original y copia solicitando la exclusión con el formulario de solicitud.',
            'Copia del DNI del firmante y documentación que acredite representación o personería.',
            'Constancia de inscripción en AFIP y en DGR Misiones o Convenio Multilateral.',
            'Detalle de operaciones gravadas de los últimos 6 meses y proyección de los próximos 12, certificado por contador público.',
            'Detalle de percepciones y retenciones del período, certificado por contador público.',
            'Evolución del saldo a favor de los últimos 6 meses, certificada por contador público.',
            'Detalle de deudas pendientes con el organismo fiscal por distintos tributos.',
        ],
        20,
        tema='Impuestos',
        sedes='posadas_agentes',
    ),
    posadas(
        'Recolección de ramas y residuos',
        'Servicio municipal de retiro de ramas y residuos de gran volumen, con pago del canon correspondiente.',
        [
            'Informar en Inspección General, en el subsuelo de la Municipalidad o en la delegación más cercana, la cantidad de metros cúbicos a retirar.',
            'Abonar el canon de la Ordenanza Tributaria XVII/N° 15.',
            'El Director de Recolección coordina con el contribuyente la fecha del servicio.',
        ],
        23,
        tema='Servicios Públicos',
        sedes='posadas_servicios',
    ),
    posadas(
        'Solicitud de poda de arbolado urbano',
        'Autorización municipal para podar árboles urbanos y retirar los residuos generados.',
        [
            'Iniciar expediente con la Nota de Solicitud de Poda en mesa de entrada o en la delegación más cercana.',
            'Recibir la boleta de inspección de arbolado de los inspectores ambientales.',
            'Abonar el canon correspondiente a la Ordenanza Tributaria.',
            'Esperar el operativo integral de poda o coordinar con un podador urbano artesanal inscripto.',
            'Para corte al ras: la Dirección de Restauración Ambiental emite una ficha técnica que decide si corresponde.',
        ],
        23,
        tema='Ambiente',
        sedes='posadas_servicios',
    ),
    posadas(
        'Inscripción en el Registro de Administradores de Consorcios',
        'Registro municipal de personas físicas o jurídicas que administran consorcios de propiedad horizontal en Posadas.',
        [
            'Nota de solicitud con carácter de declaración jurada.',
            'Datos de identidad completos; personas jurídicas: contrato social, modificaciones y última designación de autoridades.',
            'CUIT o CUIL con constancia vigente y copia del DNI.',
            'Domicilio real y/o especial en Posadas.',
            'Teléfono y correo electrónico actualizados.',
            'Acta de Asamblea certificada con la designación del administrador, datos del consorcio y cantidad de unidades funcionales.',
        ],
        31,
        tema='Vivienda',
        sedes='posadas_obras',
    ),
    posadas(
        'Certificado de funcionamiento comercial',
        'Certificado municipal de funcionamiento para locales comerciales, con documentación técnica firmada por profesional habilitado.',
        [
            'Plano de arquitectura con detalle funcional, propuesta y ubicación del equipamiento a instalar.',
            'Plano en planta acotado con niveles, cortes, vistas y alturas.',
            'Instalación eléctrica: detalle de tablero, circuitos y ubicación de bocas, tomas y tableros.',
            'Instalación sanitaria: plano acotado con artefactos, cámaras de inspección y conexión a cloaca o pozo absorbente.',
            'Instalación de gas: plano acotado con artefactos, almacenamiento y distribución; certificado de auditoría de gas.',
            'Toda la documentación tiene carácter de declaración jurada y debe estar firmada por profesional habilitado.',
        ],
        33,
        tema='Comercio',
        sedes='posadas_obras',
    ),
    posadas(
        'Licencia de conducir para clases profesionales C, D y E',
        'Inicio o renovación de licencias profesionales jurisdiccionales e interjurisdiccionales para conducir vehículos de mayor complejidad.',
        [
            'Último ejemplar del DNI con domicilio en Posadas, original y copia.',
            'Tener 1 año de antigüedad en la clase de auto B1-B2.',
            'Presentar la licencia anterior.',
            'Apto psicológico y examen psicofísico en la sede del CAV Hiper.',
            'Clases D1, D2 y D3: antecedentes penales nacionales con validez de 30 días.',
            'La licencia profesional interjurisdiccional se tramita online en seguridadvial.gob.ar y el psicofísico se hace en prestadores habilitados por la ANSV.',
            'Límite de edad para solicitarla por primera vez: 65 años.',
        ],
        37,
        tema='Tránsito',
        sedes='posadas_licencias',
    ),
    posadas(
        'Primera licencia de conducir para clases particulares A, B y G',
        'Otorgamiento de la licencia nacional de conducir para automóviles y motos, con curso y exámenes.',
        [
            'Presentarse en mesa de entrada del centro de emisión con el DNI y la documentación según la condición del solicitante.',
            'Generar el Formulario Único de Trámite (FUT) en el box de atención.',
            'Realizar el examen psicofísico en la oficina médica.',
            'Realizar el curso de Educación Vial y aprobar los exámenes teórico y práctico.',
            'Abonar la boleta del costo de la licencia en Caja y presentar la documentación para la impresión.',
            'La licencia emitida se visualiza en la aplicación Mi Argentina.',
        ],
        38,
        tema='Tránsito',
        sedes='posadas_licencias',
    ),
    posadas(
        'Renovación de licencia de conducir para clases particulares A, B y G',
        'Renovación de la licencia nacional de conducir para automóviles y motos.',
        [
            'Presentarse en mesa de entrada del centro de emisión con el DNI y la documentación según la condición del solicitante.',
            'Generar el Formulario Único de Trámite (FUT) en el box de atención.',
            'Realizar el examen psicofísico en la oficina médica.',
            'Abonar la boleta del costo de la licencia en Caja.',
            'Presentar la documentación y aguardar la impresión; la licencia queda disponible en Mi Argentina.',
        ],
        39,
        tema='Tránsito',
        sedes='posadas_licencias',
    ),
])

# ---------------------------------------------------------------------------
# Administración Tributaria de Misiones (ATM)
# ---------------------------------------------------------------------------

ATM_IB = 'https://atmisiones.gob.ar/ingresos-brutos-autogestion/'
ATM_INM = 'https://atmisiones.gob.ar/inmobiliario-autogestion/'
ATM_SELLOS = 'https://atmisiones.gob.ar/sellos-autogestion/'


def atm(titulo, descripcion, requisitos, url, *, fuente, destacado=False):
    return _ficha(
        titulo, 'Impuestos', 'virtual', 'Posadas', ATM, descripcion, requisitos,
        [('Autogestión tributaria de ATM', url)],
        [(url, fuente)],
        SEDES['atm'], destacado,
    )


TRAMITES.extend([
    atm(
        'Cambio de nivel de clave fiscal',
        'Solicitud de aumento del nivel de la clave fiscal para operar con más servicios de la ATM.',
        [
            'Contar con clave fiscal Nivel 1.',
            'Adjuntar por Legajo Único la documentación requerida en el Artículo 5 de la RG 14/2023.',
            'Ingresar a la Extranet, menú Contribuyente, para gestionar el cambio.',
            'Aguardar la notificación en la Ventanilla Electrónica.',
        ],
        ATM_IB,
        fuente='Procedimiento y requisitos del cambio de nivel de clave fiscal',
    ),
    atm(
        'Alta, modificación o cese de actividades (SR311)',
        'Formulario para iniciar, modificar o dar de baja una actividad en Ingresos Brutos o como agente de recaudación.',
        [
            'Completar el formulario SR311 con el motivo: inscripción, modificación de datos o cese.',
            'Adjuntar la documentación correspondiente al Legajo Único.',
            'Presentar el formulario online y aguardar la notificación en la Ventanilla Electrónica.',
        ],
        ATM_IB,
        fuente='Descripción, motivos y consideraciones del formulario SR311',
        destacado=True,
    ),
    atm(
        'Declaración Jurada mensual de Ingresos Brutos (SR318)',
        'Presentación mensual de los ingresos percibidos por contribuyentes directos del impuesto sobre los Ingresos Brutos.',
        [
            'Estar inscripto como contribuyente directo en Ingresos Brutos.',
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'Consultar el calendario de vencimientos del tributo en el portal de ATM.',
        ],
        ATM_IB,
        fuente='Descripción, requisitos y estados del formulario SR318',
        destacado=True,
    ),
    atm(
        'Declaración Jurada anual de Ingresos Brutos (SR320)',
        'Presentación anual del ejercicio fiscal para contribuyentes directos del impuesto sobre los Ingresos Brutos.',
        [
            'Poseer clave fiscal Nivel 2.',
            'Registrar inscripción en el impuesto sobre los Ingresos Brutos.',
            'Tener presentadas las declaraciones juradas mensuales sin observaciones.',
        ],
        ATM_IB,
        fuente='Descripción y requisitos del formulario SR320',
    ),
    atm(
        'Declaración Jurada mensual de agente de retención (SR128)',
        'Declaración y pago de las retenciones de Ingresos Brutos practicadas por agentes de retención.',
        [
            'Estar inscripto como contribuyente en el impuesto.',
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'Consultar el calendario de vencimientos del tributo.',
        ],
        ATM_IB,
        fuente='Descripción y requisitos del formulario SR128',
    ),
    atm(
        'Declaración Jurada mensual de agente de percepción (SR129)',
        'Declaración y pago de las percepciones de Ingresos Brutos practicadas por agentes de percepción.',
        [
            'Estar inscripto como contribuyente en el impuesto.',
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'Consultar el calendario de vencimientos del tributo.',
        ],
        ATM_IB,
        fuente='Descripción y requisitos del formulario SR129',
    ),
    atm(
        'Declaración Jurada mensual de pagos a cuenta (SR343)',
        'Declaración informativa mensual de los contribuyentes que pagan anticipos de Ingresos Brutos mediante el Sistema Especial de Pagos.',
        [
            'Estar inscripto como contribuyente en el impuesto.',
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'Consultar el calendario de vencimientos del tributo.',
        ],
        ATM_IB,
        fuente='Descripción y requisitos del formulario SR343',
    ),
    atm(
        'Constancia de cumplimiento de obligaciones fiscales (SR322)',
        'Solicitud de la constancia que acredita el cumplimiento de las obligaciones fiscales provinciales.',
        [
            'Ingresar con CUIT y clave fiscal Nivel 2.',
            'Registrar inscripción en Ingresos Brutos.',
            'Solicitar el certificado cuando la facturación supere los $250.000.',
        ],
        ATM_IB,
        fuente='Descripción, requisitos y consideraciones del formulario SR322',
    ),
    atm(
        'Alta de Certificado Fiscal para Contratar (SR345)',
        'Solicitud de alta del certificado que permite contratar con el Estado provincial y generar el formulario SR348.',
        [
            'Ingresar con CUIT y clave fiscal Nivel 2.',
            'Registrar inscripción en Ingresos Brutos.',
            'El certificado tiene una vigencia de 120 días.',
        ],
        ATM_IB,
        fuente='Descripción, requisitos y vigencia del formulario SR345',
    ),
    atm(
        'Emisión de Certificado Fiscal para Contratar (SR348)',
        'Emisión del certificado fiscal para contratar a partir de un SR345 vigente.',
        [
            'Ingresar con CUIT y clave fiscal Nivel 2.',
            'Registrar inscripción en Ingresos Brutos.',
            'Contar con un SR345 vigente.',
            'El vencimiento del SR349 coincide con el del SR345.',
        ],
        ATM_IB,
        fuente='Descripción, requisitos y consideraciones del formulario SR348',
    ),
    atm(
        'Exclusiones, compensaciones y devoluciones (SF178)',
        'Solicitud de exclusión de regímenes, reducción de alícuotas, compensación, cesión de saldos y devoluciones.',
        [
            'Contar con clave fiscal y Domicilio Fiscal Electrónico constituido.',
            'Seleccionar el motivo de la solicitud: exclusión, reducción, compensación, cesión, devolución o reintegro.',
            'Presentar la documentación en PDF que exige el motivo, con un máximo de 5 MB.',
        ],
        ATM_IB,
        fuente='Descripción, requisitos, motivos y formato de archivos del formulario SF178',
    ),
    atm(
        'Solicitud de exención de Sellos (SR352)',
        'Solicitud de exención del pago de un instrumento alcanzado por una resolución de la ATM.',
        [
            'Poseer clave fiscal Nivel 2.',
            'Tener constituido el Domicilio Fiscal Electrónico.',
            'Adjuntar la documentación en PDF, con un máximo de 5 MB.',
            'Se recomienda usar Mozilla Firefox para el trámite.',
        ],
        ATM_SELLOS,
        fuente='Descripción, requisitos y consideraciones del formulario SR352',
    ),
    atm(
        'Cambio de titular o contribuyente inmobiliario (SR308)',
        'Solicitud de cambio del titular del impuesto inmobiliario de un inmueble.',
        [
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'Presentar documentación que acredite la titularidad: cesión de derechos, boleto de compraventa, adjudicación de EBY o IPRODHA, permiso de ocupación, título de propiedad o sentencia judicial por usucapión.',
        ],
        ATM_INM,
        fuente='Descripción, requisitos y documentación del formulario SR308',
    ),
    atm(
        'Certificado de libre deuda inmobiliario (SR309)',
        'Solicitud del certificado que acredita que un inmueble no registra deudas del impuesto inmobiliario.',
        [
            'Identificarse con CUIT y Clave de Identificación Tributaria.',
            'El formulario puede ser solicitado por escribanos, abogados o martilleros.',
        ],
        ATM_INM,
        fuente='Descripción, requisitos y consideraciones del formulario SR309',
    ),
])

# ---------------------------------------------------------------------------
# Instituto Provincial de Desarrollo Habitacional (IPRODHA)
# ---------------------------------------------------------------------------

IPRODHA_URL = 'https://iprodha.misiones.gob.ar/'


def iprodha(titulo, descripcion, requisitos, slug, *, tema='Vivienda',
            destacado=False):
    url = IPRODHA_URL + slug
    return _ficha(
        titulo, tema, 'presencial', 'Posadas', IPRODHA, descripcion, requisitos,
        [('Guía de trámites de IPRODHA', url)],
        [(url, 'Título, descripción y requisitos del programa')],
        SEDES['iprodha'], destacado,
    )


TRAMITES.extend([
    iprodha(
        'Inscripción en el Registro de Demanda General de Viviendas',
        'Inscripción para acceder a una vivienda social en la localidad donde la persona habita de forma permanente.',
        [
            'Ser ciudadano argentino o extranjero con residencia legal debidamente probada y con hijos nacidos en el país.',
            'Haber vivido de forma permanente y habitual en la localidad donde se inscribe.',
            'Prioridad para grupos familiares con hijos menores o con integrantes con discapacidad.',
            'Contar con ingresos suficientes para pagar la vivienda y mantener la calidad de vida.',
            'Presentar codeudor y bancarización de ingresos que aseguren el cumplimiento de las obligaciones.',
            'Informar un domicilio electrónico fidedigno: las convocatorias se envían únicamente por correo.',
            'Actualizar la inscripción cada 360 días corridos antes de la convocatoria.',
            'No haber sido adjudicatario de vivienda ni beneficiario de un préstamo social, salvo nuevo grupo familiar con cesión de derechos.',
            'Acreditar judicialmente la tenencia de los hijos menores de edad.',
            'Ningún integrante del grupo conviviente puede ser propietario de una vivienda o de un inmueble realizable equivalente.',
        ],
        'viviendas-2/',
        destacado=True,
    ),
    iprodha(
        'Construcción de Viviendas Rurales',
        'Programa de construcción de viviendas rurales gestionado a través de municipios, cooperativas o asociaciones con convenio con IPRODHA.',
        [
            'Inscribirse en el municipio o centro de atención del IPRODHA.',
            'Fotocopia del DNI, anverso y reverso, de todos los integrantes del grupo familiar conviviente.',
            'Fotocopia del acta de matrimonio o certificado de unión convivencial.',
            'Fotocopia del dominio: título, boleto de compraventa certificado, permiso de ocupación actualizado o constancia de ocupación de Tierras.',
            'Factura de venta de productos de la chacra, recibo de haberes o declaración jurada de ingresos expedida por la Policía.',
            'Constancia de CBU de caja de ahorro; si no posee, garante solidario.',
            'Contar con servicio de energía y presentar factura del proveedor.',
            'Contar con agua de red, perforación, vertiente o pozo.',
            'No haber sido beneficiado por ningún programa del IPRODHA.',
            'Aceptar el pago en 360 cuotas mensuales o 30 cuotas anuales.',
            'Toda la documentación debe estar certificada por Policía, Juzgado, Escribano o Intendente.',
            'El municipio, cooperativa o asociación presenta nota al Presidente del IPRODHA, plano georreferenciado, resolución del representante técnico y fichas de inscripción.',
        ],
        'construccion-de-viviendas-rurales-2/',
    ),
    iprodha(
        'Construcción de Viviendas de Gestión Compartida',
        'Programa para construir viviendas en terrenos municipales donados al IPRODHA, con aporte financiero del municipio.',
        [
            'Ficha de inscripción del grupo familiar.',
            'Fotocopia del DNI, anverso y reverso, de todos los integrantes del grupo familiar conviviente.',
            'El municipio debe presentar la documentación de dominio de los terrenos.',
            'Ordenanza del Concejo Deliberante que dona los terrenos a favor del IPRODHA.',
            'Documentación que acredite la factibilidad de los servicios públicos.',
            'Planos de ubicación del inmueble con coordenadas geográficas.',
            'Propuesta de urbanización y loteo.',
            'Ordenanza del Concejo Deliberante que autoriza el descuento en la coparticipación municipal.',
        ],
        'construccion-de-viviendas-de-gestion-compartida/',
    ),
    iprodha(
        'Arreglo Mi Casa',
        'Programa de refacción o ampliación de viviendas existentes para grupos familiares beneficiarios de IPRODHA.',
        [
            'Fotocopia del DNI, anverso y reverso, de todos los integrantes del grupo familiar conviviente.',
            'Si hay integrantes con discapacidad: certificación del Ministerio de Salud Pública de Misiones.',
            'Fotocopia del CUIL.',
            'Título de propiedad, permiso de ocupación de Tierras o boleto de compraventa ante escribano.',
            'Fotocopia de una boleta de servicio del titular con el domicilio declarado completo y claro.',
            'Recibos de sueldo, pensión o asignación familiar del grupo familiar.',
            'CBU emitida por ventanilla del banco si cobra por cajero automático.',
            'Trabajadores independientes: declaración jurada de todos los ingresos ante Juzgado de Paz.',
        ],
        'arreglo-mi-casa/',
    ),
    iprodha(
        'Construyo Mi Casa',
        'Crédito para construir una vivienda en un lote propio, destinado a grupos familiares con al menos un menor de 18 años.',
        [
            'El titular no debe superar los 60 años de edad.',
            'Fotocopia del DNI, anverso y reverso, de todos los integrantes del grupo familiar conviviente.',
            'Partidas de nacimiento de los hijos menores; al menos un integrante debe tener menos de 18 años al entregar la vivienda.',
            'Acta de matrimonio o certificado de unión convivencial; si está en trámite, certificado de convivencia policial.',
            'Divorciados: sentencia de divorcio. Disolución del grupo familiar anterior: sentencia o constancia de trámite iniciado.',
            'Padre o madre solo con hijos a cargo: partida de nacimiento y certificado de convivencia, o constancia judicial de guarda.',
            'Constancia del Registro de la Propiedad de que el titular, cónyuge o concubino no es titular de una vivienda.',
            'Título de propiedad del lote a construir.',
            'Trabajadores en relación de dependencia: recibo de sueldo y CBU; empleados públicos con descuento por planilla.',
            'Trabajadores independientes: formulario SR318 de Rentas, comprobantes de Ingresos Brutos y pagos de monotributo o autónomos de los últimos 3 meses.',
            'Ex beneficiarios de Lotes con Servicio: codeudor con relación laboral dependiente del Estado nacional, provincial o municipal.',
            'Alternativa para otros postulantes: garantía hipotecaria sobre el terreno o codeudor con relación laboral estatal.',
            'Toda la documentación debe estar certificada por escribano, juez de paz o comisaría.',
        ],
        'construyo-mi-casa/',
    ),
    iprodha(
        'Mediación entre Terceros para Regularización Dominial',
        'Intervención del IPRODHA para regularizar terrenos particulares ocupados por familias durante más de cinco años.',
        [
            'Los terrenos deben ser de dominio particular y estar ocupados por grupos de personas o familias por más de 5 años.',
            'El titular dominial debe solicitar la intervención mediante nota dirigida al Presidente del IPRODHA.',
            'Acompañar documentación acreditante del dominio y titularidad: título, plano de mensura y documentación para determinar las fracciones.',
            'Se formará un expediente administrativo con los análisis técnicos y dominiales.',
        ],
        'requisitos-mediacion-entre-terceros/',
    ),
    iprodha(
        'Beneficio para Personas Trasplantadas',
        'Subsidio del 40% para beneficiarios de programas habitacionales que acrediten trasplante o estar en lista de espera.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Presentar la credencial para trasplantados de INCUCAI.',
            'Fotocopia del DNI del solicitante.',
            'Estar al día con las cuotas del beneficio.',
            'El subsidio rige mientras esté vigente la credencial de INCUCAI; en viviendas sustentables se reduce al 10%.',
        ],
        'beneficio-para-personas-trasplantadas/',
    ),
    iprodha(
        'Beneficios para Personas con CUD',
        'Subsidio del 40% para beneficiarios de programas habitacionales que acrediten discapacidad mediante CUD.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Presentar el Certificado Único de Discapacidad (CUD).',
            'Fotocopia del DNI del solicitante.',
            'Estar al día con las cuotas del beneficio.',
            'Para renovar: presentar la nota y el certificado del nuevo CUD en trámite antes del vencimiento.',
        ],
        'beneficios-cud/',
    ),
    iprodha(
        'Cancelación por Fallecimiento',
        'Cancelación del 50% de la deuda de la vivienda para cónyuge o conviviente del beneficiario fallecido.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Fotocopia del acta de defunción con certificado original del Registro o acta con sello digital.',
            'Fotocopia del DNI del denunciante, anverso y reverso.',
            'Estar al día con las cuotas de amortización.',
        ],
        'cancelacion-por-fallecimiento/',
    ),
    iprodha(
        'Cancelación Anticipada',
        'Cancelación total anticipada del saldo de la vivienda financiada por IPRODHA.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Fotocopia de la boleta de cancelación total intervenida por el banco.',
            'Fotocopia del DNI del titular del beneficio.',
        ],
        'cancelacion-anticipada/',
    ),
    iprodha(
        'Cambio de Titular de la Vivienda',
        'Transferencia del titular de una vivienda IPRODHA a otro integrante del grupo familiar original, con ingresos y garantías.',
        [
            'El solicitante debe ser parte del grupo familiar original de la adjudicación.',
            'La vivienda debe estar al día en el pago de las cuotas.',
            'El nuevo titular debe presentar ingresos y garantías para continuar el pago.',
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Persona casada: sentencia de divorcio con separación de bienes.',
            'Unión de hecho: renuncia del condominio ante escribano público.',
        ],
        'cambio-de-titular/',
    ),
    iprodha(
        'Denuncia de Siniestro en la Vivienda',
        'Denuncia de daños sufridos en una vivienda financiada por IPRODHA para evaluar la cobertura o las medidas a adoptar.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Estar al día con las cuotas del beneficio.',
            'Presentar la exposición policial del siniestro.',
            'En caso de incendio, adjuntar el informe de los bomberos.',
            'Fotocopia del DNI del solicitante.',
        ],
        'denuncia-de-siniestro/',
    ),
    iprodha(
        'Renuncia a la Vivienda',
        'Renuncia voluntaria del adjudicatario a una vivienda financiada por IPRODHA.',
        [
            'Presentar nota formal en mesa de entrada, por duplicado.',
            'Si existe convenio de pago por deuda de recapitalización, cancelarlo en su totalidad.',
            'Si la vivienda tiene título de propiedad, otorgar poder especial e irrevocable a favor del IPRODHA para el distracto notarial.',
            'Presentar libre deuda de servicios: luz, agua e impuestos.',
        ],
        'renuncia-la-vivienda/',
    ),
    iprodha(
        'Permiso de Custodia o Guarda de la Vivienda',
        'Autorización para que otra persona o grupo familiar ocupe temporalmente una vivienda IPRODHA mientras el adjudicatario se ausenta.',
        [
            'Presentar por escrito el pedido fundado, explicando los motivos de la ausencia.',
            'Si el solicitante es casado, ambos cónyuges deben firmar; igual criterio para condominios o grupos familiares.',
            'Concubinos no declarados en la adjudicación: certificado de convivencia expedido por la Justicia de Paz.',
            'Presentar certificado de traslado laboral o certificado de salud de un centro de alta complejidad que justifique el traslado.',
            'Copias y originales del DNI de la persona o grupo que ocupará la vivienda; no pueden tener un beneficio IPRODHA activo.',
            'Ser adjudicatario de un plan de venta.',
            'Estar al día con el pago de las cuotas.',
            'Firmar el formulario modelo del IPRODHA el adjudicatario y el custodio de la vivienda.',
        ],
        'permiso-de-custodia-o-guarda/',
    ),
])

# ---------------------------------------------------------------------------
# Energía de Misiones
# ---------------------------------------------------------------------------

ENERGIA_PORTAL = 'https://clientes.energiademisiones.com.ar/clientes/tramites/listar-tramites/ver-tramite/'
ENERGIA_TARIFA = 'https://www.energiademisiones.com.ar/tarifa-social/'
ENERGIA_ELECTRO = 'https://www.energiademisiones.com.ar/electrodependientes/'


def energia(titulo, descripcion, requisitos, *, url, fuente, sedes='energia',
            destacado=False):
    return _ficha(
        titulo, 'Servicios Públicos', 'virtual', 'Posadas', ENERGIA,
        descripcion, requisitos,
        [('Portal de trámites de Energía de Misiones', url)],
        [(url, fuente)],
        SEDES[sedes], destacado,
    )


TRAMITES.extend([
    energia(
        'Habilitación inicial del servicio eléctrico',
        'Conexión nueva del suministro eléctrico con instalación de medidor en el domicilio.',
        [
            'Disponer del pilar reglamentario monofásico o trifásico en condiciones técnicas óptimas.',
            'Si no es propietario, abonar el depósito de garantía según categoría y potencia.',
            'DNI del titular o autorización con poder ante escribano o juez de paz y DNI del autorizado.',
            'Constancia de CUIT no excluyente y documentación societaria que acredite la representación.',
            'Título de propiedad, boleto de compra o documento que acredite la propiedad, sellado por ATM.',
            'Contrato de locación o comodato sellado y timbrado por ATM.',
            'Certificación de número de finca expedida por la Municipalidad.',
            'Abonar el arancel: monofásico $100.000; trifásico de 1 a 10 kW $150.000; de 11 a 299 kW $300.000; media tensión $450.000.',
        ],
        url=ENERGIA_PORTAL + '19',
        fuente='Descripción, aranceles y requisitos de la habilitación inicial',
        destacado=True,
    ),
    energia(
        'Cambio de titularidad del servicio eléctrico',
        'Cambio del servicio de energía a nombre del nuevo titular de la conexión.',
        [
            'Datos del usuario anterior: factura de consumo o número de conexión.',
            'Disponer del pilar reglamentario en condiciones técnicas óptimas.',
            'Si no es propietario, abonar el depósito de garantía correspondiente.',
            'DNI del nuevo titular o autorización con poder y DNI del autorizado.',
            'Constancia de CUIT y documentación societaria que acredite la representación, cuando corresponda.',
            'Título de propiedad, boleto de compra o documento que acredite la propiedad, sellado por ATM.',
            'Contrato de locación o comodato sellado por ATM.',
            'Certificación de número de finca expedida por la Municipalidad.',
            'Abonar el arancel de $30.000.',
        ],
        url=ENERGIA_PORTAL + '24',
        fuente='Descripción, arancel y requisitos del cambio de titularidad',
    ),
    energia(
        'Baja del servicio eléctrico',
        'Baja de la conexión eléctrica con retiro del medidor del domicilio.',
        [
            'La conexión no debe poseer deuda, aunque el requisito no es excluyente.',
            'DNI del titular o autorización con poder ante escribano o juez de paz y DNI del autorizado.',
            'Constancia de CUIT y documentación societaria que acredite la representación, cuando corresponda.',
            'El trámite no tiene costo.',
        ],
        url=ENERGIA_PORTAL + '32',
        fuente='Descripción, arancel y requisitos de la baja del servicio',
    ),
    energia(
        'Beneficio para jubilados y pensionados',
        'Descuento provincial para jubilados y pensionados con ingresos bajos y una sola conexión residencial.',
        [
            'Pertenecer a la categoría residencial.',
            'Tener un sueldo inferior al Salario Mínimo Vital y Móvil vigente.',
            'No poseer deuda con la empresa.',
            'No tener más de una conexión.',
            'Renovar el beneficio cada 6 meses.',
            'Presentar DNI o autorización con poder y DNI del autorizado.',
            'Presentar el recibo de sueldo del mes inmediato anterior.',
        ],
        url=ENERGIA_PORTAL + '33',
        fuente='Descripción, condiciones y requisitos del beneficio jubilado y pensionado',
    ),
    energia(
        'Devolución del depósito de garantía',
        'Reintegro del depósito abonado por usuarios no propietarios luego de la baja de una conexión sin deuda.',
        [
            'No poseer deuda.',
            'Haber dado de baja la conexión.',
            'Solicitar la devolución después de los 45 días de pedir la baja.',
            'Especificar la forma de devolución: cancelación de comprobante, crédito en otra conexión o transferencia bancaria.',
        ],
        url=ENERGIA_PORTAL + '65',
        fuente='Descripción, condiciones y requisitos de la devolución del depósito',
    ),
    energia(
        'Devolución por pago doble',
        'Crédito a favor del usuario por el pago duplicado de una misma factura.',
        [
            'Especificar la forma de devolución: cancelación de comprobante, crédito en otra conexión o transferencia bancaria.',
        ],
        url=ENERGIA_PORTAL + '66',
        fuente='Descripción y requisitos de la devolución por pago doble',
    ),
    energia(
        'Revisión de factura',
        'Reclamo cuando el usuario considera que el importe facturado es excesivo por consumo o tarifa.',
        [
            'No requiere documentación según el portal de Energía de Misiones.',
        ],
        url=ENERGIA_PORTAL + '67',
        fuente='Descripción y requisitos de la revisión de factura',
    ),
    energia(
        'Adhesión al débito automático',
        'Autorización para debitar automáticamente la factura eléctrica de una cuenta bancaria.',
        [
            'DNI del titular o autorización con poder y DNI del autorizado.',
            'Constancia de CUIT y documentación societaria que acredite la representación, cuando corresponda.',
            'Comprobante con número de cuenta bancaria y CBU emitido por home banking, sucursal o cajero automático.',
        ],
        url=ENERGIA_PORTAL + '68',
        fuente='Descripción y requisitos de la adhesión al débito automático',
    ),
    energia(
        'Factibilidad eléctrica',
        'Análisis de la red para determinar si es posible conectar un suministro o si hace falta una obra eléctrica previa.',
        [
            'Ubicación exacta del inmueble con punto GPS, sin excepción.',
            'Puesto de medición listo para la conexión según la R.G.S.E. vigente.',
            'No poseer deudas de servicios públicos ni actas de infracción.',
            'Abonar el anticipo del arancel del proyecto e inspección según la potencia solicitada.',
            'DNI del titular o autorización con poder y DNI del autorizado.',
            'Constancia de CUIT y documentación societaria que acredite la representación, cuando corresponda.',
            'Título de propiedad, boleto de compra o documento que acredite la propiedad, sellado por ATM.',
            'Certificación de número de finca expedida por la Municipalidad.',
            'Formulario B: Declaración Jurada de Cargas de Propiedad Horizontal, cuando corresponda.',
            'Plano eléctrico o plano de loteo aprobado por la Municipalidad; para loteo, plano aprobado por agrimensor.',
        ],
        url=ENERGIA_PORTAL + '69',
        fuente='Descripción, aranceles y requisitos de factibilidad eléctrica',
        destacado=True,
    ),
    energia(
        'Tarifa Social provincial',
        'Beneficio tarifario para hogares en situación de vulnerabilidad que cumplan los criterios de elegibilidad provinciales.',
        [
            'Ser jubilado o pensionado por un monto equivalente a dos veces el haber mínimo nacional.',
            'Tener empleo en relación de dependencia con remuneración bruta menor o igual a 2 salarios mínimos vitales y móviles.',
            'Ser titular de programas sociales o estar inscripto en el Monotributo Social.',
            'Estar incorporado al régimen especial de servicio doméstico o percibir seguro de desempleo.',
            'No ser titular de más de un inmueble.',
            'No poseer automotores de hasta 10 años de antigüedad, aeronaves o embarcaciones de lujo.',
            'No figurar en el padrón de fallecidos.',
        ],
        url=ENERGIA_TARIFA,
        fuente='Criterios de elegibilidad y exclusión de la Tarifa Social',
        destacado=True,
    ),
    energia(
        'Registro de Electrodependientes (RECS)',
        'Inscripción o renovación en el registro que otorga gratuidad del servicio eléctrico a personas que dependen de equipos médicos.',
        [
            'DNI original del paciente, último ejemplar, para obtener el número de trámite.',
            'Si el paciente es menor: partida de nacimiento y DNI de ambos padres o tutores.',
            'Constancia de CUIL si no figura en el DNI.',
            'Formulario FRECS completo, con firma y aclaración del paciente, padre, madre o tutor.',
            'Certificado del médico tratante con patología, equipamiento y estudios médicos de no más de un año.',
            'Factura del servicio eléctrico del domicilio del paciente, con dirección coincidente con el formulario y el DNI.',
            'Si el titular no es el paciente: documentación que acredite el vínculo.',
            'Certificado de domicilio si el domicilio real no coincide con el del DNI.',
            'Estudio de sueño si el diagnóstico es apnea.',
        ],
        url=ENERGIA_ELECTRO,
        fuente='Descripción y requisitos de inscripción y renovación del RECS',
        sedes='energia_electro',
        destacado=True,
    ),
])

# ---------------------------------------------------------------------------
# SAMSA - Aguas de Misiones
# ---------------------------------------------------------------------------

SAMSA_URL = 'https://samsa.com.ar/'


def samsa(titulo, descripcion, requisitos, slug, *, destacado=False):
    url = SAMSA_URL + slug
    return _ficha(
        titulo, 'Servicios Públicos', 'presencial', 'Posadas', SAMSA,
        descripcion, requisitos,
        [('Sitio de SAMSA', url)],
        [(url, 'Título, descripción y requisitos del trámite')],
        SEDES['samsa'], destacado,
    )


TRAMITES.extend([
    samsa(
        'Solicitud de conexión domiciliaria de agua y cloaca',
        'Conexión nueva de agua potable y/o cloaca para un inmueble, con presupuesto previo y pago de derechos.',
        [
            'Solicitar el presupuesto de los costos de conexión; se entrega dentro de las 48 horas.',
            'DNI del titular o responsable del inmueble, fotocopia y original para verificación.',
            'Título de propiedad o boleto de compraventa autenticado por escribano, fotocopia y original.',
            'Plano de mensura solicitado en Catastro de la Provincia.',
            'Estar libre de deuda en la cuenta de SAMSA o regularizarla antes de la conexión.',
            'Croquis sanitario del inmueble avalado por un profesional competente.',
            'Solicitud de conexión completada y firmada, formulario oficial que se retira en oficinas.',
            'Comprobante de pago de derechos de conexión, abonado en tesorería o banco habilitado.',
            'El trámite debe realizarlo el propietario del inmueble; la documentación incompleta no se recibe.',
        ],
        'solicitud-conexion-domiciliaria/',
        destacado=True,
    ),
    samsa(
        'Cambio de titularidad del servicio de agua',
        'Cambio a nombre del nuevo titular de una cuenta de agua y/o cloaca existente.',
        [
            'Título de propiedad o boleto de compraventa certificado ante escribano.',
            'Posesión veinteñal, cuando corresponda.',
            'Fotocopia del DNI.',
            'Firma de la nota solicitando el cambio de titularidad.',
            'Casos particulares: certificado de adjudicación, contrato de comodato, cesión de derechos, contrato de alquiler u otros.',
        ],
        'cambio-de-titularidad/',
    ),
    samsa(
        'Constancia de servicio de agua y/o cloaca',
        'Constancia que acredita la existencia y las condiciones del servicio de agua y/o cloaca de un inmueble.',
        [
            'Número de cuenta del inmueble, sin deuda vencida.',
            'Si no es cliente existente: presentar plano de mensura.',
            'Abonar el costo preestablecido según el código de facturación.',
        ],
        'constancia-de-servicio/',
    ),
    samsa(
        'Libre deuda de SAMSA',
        'Certificado que acredita que la cuenta del inmueble no registra deudas con SAMSA.',
        [
            'Número de cuenta de la propiedad, que no debe registrar deuda.',
            'El trámite no tiene costo.',
        ],
        'libre-deuda/',
        destacado=True,
    ),
    samsa(
        'Corrección de datos de la cuenta',
        'Corrección de dirección, datos catastrales, datos de calle, situación, cambio de base, IVA o alta y baja de cuenta.',
        [
            'Certificado de finca expedido por la Municipalidad de Posadas para actualizar dirección, datos catastrales y número de inmueble.',
            'Plano de mensura aprobado por la Dirección General de Catastro o informe del RPI.',
            'Consumidores finales: DNI, LC, LE o CI.',
            'Responsables inscriptos, exentos, monotributistas e IVA no alcanzado: CUIT con la inscripción respectiva.',
            'Alta de cuenta: solicitud de conexión de agua y/o cloaca con documentación, o nota de aviso e inspección catastral para radio servido.',
            'Baja de cuenta: informe RPI o DGC por duplicidad, mensura por unificación catastral o nota por toma de posesión de la EBY.',
        ],
        'correccion-de-datos/',
    ),
    samsa(
        'Solicitud de factibilidad para barrios',
        'Evaluación de factibilidad de agua y cloaca para un proyecto de barrio o urbanización.',
        [
            'Plano del proyecto de obra.',
            'Plano de mensura o croquis de ubicación de la obra.',
        ],
        'solicitud-de-factibilidad-para-barrios/',
    ),
    samsa(
        'Convenio de pago de deuda',
        'Acuerdo para regularizar una deuda existente con SAMSA.',
        [
            'Título de propiedad, boleto de compraventa o certificado de adjudicación de IPRODHA.',
            'DNI del propietario.',
            'Solicitud de convenio de pago.',
        ],
        'convenio-de-pago/',
    ),
    samsa(
        'Adhesión al débito automático de SAMSA',
        'Autorización para debitar automáticamente la factura de agua y cloaca de una tarjeta o cuenta bancaria.',
        [
            'Número de tarjeta de débito o crédito, o constancia de CBU, según lo que se quiera adherir.',
            'Copia del DNI del titular de la tarjeta o cuenta bancaria.',
            'Firma del formulario de adhesión.',
        ],
        'adhesion-debito-automatico/',
    ),
    samsa(
        'Cambio de datos postales',
        'Actualización del domicilio postal o de contacto de un cliente existente de SAMSA.',
        [
            'Ser cliente existente.',
            'Número de cuenta de la propiedad.',
        ],
        'cambios-de-datos-postales/',
    ),
])

# ---------------------------------------------------------------------------
# Ministerio de Salud Pública - Saneamiento Ambiental
# ---------------------------------------------------------------------------

SALUD_DOMISANITARIOS = 'https://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES.pdf'
SALUD_COSMETICOS = 'https://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES-2.pdf'
SALUD_RDX = 'https://salud.misiones.gob.ar/wp-content/uploads/2020/06/Guia-Requisitos-Segun-equipo-de-RDX.pdf'
SALUD_NO_GENERADOR = 'https://salud.misiones.gob.ar/wp-content/uploads/2026/06/GUIA-DE-TRAMITES-4.pdf'


def salud(titulo, descripcion, requisitos, url, *, fuente, destacado=False):
    return _ficha(
        titulo, 'Salud', 'presencial', 'Posadas', SALUD, descripcion, requisitos,
        [('Guía oficial de requisitos', url)],
        [(url, fuente)],
        SEDES['salud'], destacado,
    )


TRAMITES.extend([
    salud(
        'Inscripción de establecimiento elaborador de productos domisanitarios',
        'Registro provincial de establecimientos elaboradores o fraccionadores de productos domisanitarios de uso doméstico.',
        [
            'Nota de solicitud de inscripción por duplicado, firmada por el titular, apoderado o representante legal.',
            'Formulario de solicitud de inscripción por duplicado, todas las hojas firmadas y en tamaño A4.',
            'Fotocopia del DNI de los propietarios, representante legal y director técnico.',
            'Fotocopia del título y matrícula del director técnico, que debe ser ingeniero químico, bioquímico o farmacéutico.',
            'Número de CUIT del establecimiento.',
            'Planos del establecimiento: vista y corte.',
            'Fotocopia de inscripción en Aduana para importadores o exportadores.',
            'Fotocopia del estatuto o contrato social; si es unipersonal, certificado de domicilio.',
            'Fotocopia de la habilitación municipal del local.',
            'Fotocopia del contrato con los titulares de depósitos, si corresponde.',
            'Declaración de cumplimiento de los requisitos mínimos de BPM y BPC (Resolución 708/98).',
            'El trámite es gratuito y se presenta en la Dirección de Saneamiento Ambiental.',
        ],
        SALUD_DOMISANITARIOS,
        fuente='Requisitos para establecimientos domisanitarios, presentación, costo y plazo',
        destacado=True,
    ),
    salud(
        'Inscripción de producto domisanitario',
        'Registro provincial de productos domisanitarios elaborados o fraccionados en Misiones, con certificado por producto.',
        [
            'Nota de solicitud por duplicado, firmada por el titular, apoderado o representante legal.',
            'Formulario de solicitud de inscripción por duplicado, todas las hojas firmadas y en A4.',
            'Rótulos por triplicado, en el formato en que irán en el recipiente.',
            'Para productos importados: rótulo original y 3 fotocopias.',
            'Fotocopia legalizada del certificado de libre venta en el país de origen.',
            'Fotocopia de inscripción en la Administración Nacional de Aduanas.',
            'Cartas cruzadas de vinculación entre el titular del producto y el establecimiento registrado.',
            'Acreditación de personería jurídica.',
            'Método de elaboración y métodos de control de calidad.',
            'Especificaciones fisicoquímicas de materias primas y producto terminado.',
            'Grado de pureza, procedencia, identidad, concentración y toxicidad de impurezas.',
            'Métodos analíticos, estudios de estabilidad, ensayos de efectividad y estudios toxicológicos.',
            'Tiempo de vida útil y ensayos de laboratorio de materias primas y producto terminado.',
        ],
        SALUD_DOMISANITARIOS,
        fuente='Requisitos para productos domisanitarios y documentación anexa',
    ),
    salud(
        'Inscripción de establecimiento de higiene personal, cosméticos y perfumes',
        'Registro provincial de establecimientos elaboradores, fraccionadores, envasadores y distribuidores de cosméticos y perfumes.',
        [
            'Nota de solicitud por duplicado, firmada por el titular, apoderado o representante legal.',
            'Formulario de solicitud de inscripción con todas las hojas firmadas y en A4.',
            'Copia certificada del contrato social, estatuto o DNI, según corresponda.',
            'Acreditación de la personería del representante legal o apoderado firmante.',
            'Fotocopia del DNI, título y constancia de matriculación del director técnico.',
            'El director técnico debe ser ingeniero químico, bioquímico o farmacéutico.',
            'Fotocopia del título de propiedad o contrato de locación de la estructura edilicia.',
            'Comprobantes de CUIT, DGI y DGR.',
            'Planos de planta y cortes con instalaciones sanitarias.',
            'Habilitación municipal de la estructura edilicia.',
            'Organigrama de la empresa.',
            'Contrato con el establecimiento habilitado que actuará como tercerista, si corresponde.',
            'El trámite es gratuito y se presenta por duplicado en carpeta colgante oficio.',
        ],
        SALUD_COSMETICOS,
        fuente='Requisitos para establecimientos de higiene personal, cosméticos y perfumes',
        destacado=True,
    ),
    salud(
        'Inscripción de producto de higiene personal, cosméticos y perfumes',
        'Registro provincial de productos de higiene personal, cosméticos y perfumes elaborados en Misiones.',
        [
            'Nota de solicitud por duplicado, firmada por el titular, apoderado o representante legal.',
            'Formulario de solicitud de inscripción por duplicado, todas las hojas firmadas y en A4.',
            'Proyecto de rótulos por triplicado, en el formato en que irán en el recipiente.',
            'Contrato con el establecimiento habilitado tercerista y con cada establecimiento interviniente.',
            'Declaración jurada de uso de marcas.',
            'Declaración jurada de contenidos netos y medidas.',
            'Memoria descriptiva y operativa del proceso de elaboración.',
            'Métodos de control de calidad y especificaciones fisicoquímicas.',
            'Grado de pureza, procedencia, identidad, concentración y toxicidad de impurezas.',
            'Métodos analíticos, estudios de estabilidad, efectividad y toxicológicos.',
            'Tiempo de vida útil y ensayos de laboratorio de materias primas y producto terminado.',
            'Protocolos de análisis fisicoquímicos, microbiológicos y biológicos según las propiedades declaradas.',
        ],
        SALUD_COSMETICOS,
        fuente='Requisitos para productos de higiene personal, cosméticos y perfumes',
    ),
    salud(
        'Habilitación de servicio de radiodiagnóstico y equipos emisores de radiaciones',
        'Habilitación de servicios de radiodiagnóstico, diagnóstico por imágenes, terapéuticos, laborales y equipos emisores.',
        [
            'Antes de iniciar, identificar el tipo de equipo o servicio y descargar el formulario aplicable.',
            'Presentar la nota modelo de inicio de trámite dirigida a la Dirección de Saneamiento Ambiental.',
            'Formulario 01 para rayos X convencional, arco en C, odontológico o panorámico.',
            'Formulario 02 para unidad móvil o medicina preocupacional; 03 para resonancia magnética.',
            'Formulario 04 para medicina nuclear, radioterapia, acelerador lineal, braquiterapia, PET/CT o cámara gamma.',
            'Formulario 05 para equipos mixtos PET/CT; 06 para láser/IPL; 07 para rayos X de uso industrial.',
            'Reunir la documentación técnica, profesional y de seguridad que exige el formulario correspondiente.',
            'Cumplir la Ley Nacional 17.557 y la Ley Provincial XVII N° 58, Cap. IX, Art. 38, inc. 19.',
            'La presentación completa y ordenada facilita la evaluación técnica y administrativa.',
        ],
        SALUD_RDX,
        fuente='Tipos de equipos, formularios y normativa de habilitación de radiodiagnóstico',
    ),
    salud(
        'Renovación de habilitación de equipos de rayos X, RMI y otros',
        'Renovación de la habilitación de servicios que utilizan equipos generadores de radiaciones ionizantes y no ionizantes.',
        [
            'Presentar la nota modelo de inicio de trámite.',
            'Completar el Formulario 08 de renovación de habilitación de equipos de rayos X, RMI y otros.',
            'Reunir la documentación técnica, profesional y de seguridad que exige el formulario.',
            'Cumplir la normativa nacional y provincial de protección radiológica.',
        ],
        SALUD_RDX,
        fuente='Formulario 08 y requisitos de renovación de habilitación',
    ),
    salud(
        'Certificación de establecimiento no generador de residuos patológicos',
        'Certificación para establecimientos o instituciones que no generan residuos patológicos de la categoría Y1.',
        [
            'Nota de solicitud de certificación por duplicado, firmada por el responsable o apoderado.',
            'Copia del DNI del responsable, propietario o apoderado de la institución.',
            'Copia del CUIT del establecimiento o institución.',
            'Copia del título del profesional.',
            'Copia certificada de la matrícula profesional.',
            'Copia del certificado anterior si se trata de una renovación.',
            'Presentar todo por duplicado en la Dirección de Saneamiento Ambiental; el trámite es gratuito.',
        ],
        SALUD_NO_GENERADOR,
        fuente='Requisitos y documentación para la certificación de no generador de residuos patológicos',
    ),
])

# ---------------------------------------------------------------------------
# Policía de Misiones
# ---------------------------------------------------------------------------

POLICIA_INDEX = 'https://policiamisiones.gob.ar/tramites-a-ciudadanos/'


def policia(titulo, descripcion, requisitos, url, *, fuente, destacado=False):
    return _ficha(
        titulo, 'Seguridad', 'presencial', 'Posadas', POLICIA, descripcion,
        requisitos,
        [('Formulario oficial de la Policía de Misiones', url)],
        [
            (POLICIA_INDEX, 'Índice de trámites policiales que lista el trámite y enlaza al formulario'),
            (url, fuente),
        ],
        SEDES['policia'], destacado,
    )


TRAMITES.extend([
    policia(
        'Certificado de domicilio con testigos',
        'Certificado policial que acredita el domicilio real y efectivo del solicitante mediante la declaración de dos testigos.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'Informar nacionalidad, número de DNI, edad y ocupación.',
            'Aportar el domicilio real y efectivo que se certificará.',
            'Presentar 2 testigos con DNI y domicilio declarado.',
            'Firmar el formulario el solicitante y ambos testigos.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/09/Certificado-de-domicilio-con-testigos.pdf',
        fuente='Formulario y campos exigidos para el certificado de domicilio con testigos',
        destacado=True,
    ),
    policia(
        'Certificado de domicilio sin testigos',
        'Certificado policial de domicilio para el solicitante cuyo DNI ya contiene la dirección que se quiere acreditar.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'El domicilio declarado debe constar en el DNI del solicitante.',
            'Informar nacionalidad, número de DNI, edad y ocupación.',
            'Firmar el formulario de solicitud.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/09/Certificado-de-domicilio-sin-testigos.pdf',
        fuente='Formulario y condiciones del certificado de domicilio sin testigos',
    ),
    policia(
        'Certificado de convivencia',
        'Certificado policial que acredita que dos personas conviven en un mismo domicilio, con intervención de testigos.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'Informar el domicilio real y efectivo y la fecha desde la que convive.',
            'Aportar los datos de la persona con quien convive: nombre, tipo y número de documento y vínculo.',
            'Presentar 2 testigos con DNI y domicilio.',
            'Firmar el formulario el solicitante y los testigos.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/09/Certificado-de-convivencia-con-testigos-copia-copia.pdf',
        fuente='Formulario y datos exigidos para el certificado de convivencia',
    ),
    policia(
        'Certificado de supervivencia con testigos',
        'Certificado policial que acredita que una persona vive y tiene domicilio real y efectivo, con dos testigos o apoderado.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'Informar nacionalidad, DNI, edad y domicilio real y efectivo.',
            'Presentar 2 testigos con DNI, nacionalidad y edad, o un apoderado.',
            'Firmar el formulario el solicitante, los testigos o el apoderado.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/09/Certificado-de-supervivencia-con-testigos-1.pdf',
        fuente='Formulario y datos exigidos para el certificado de supervivencia con testigos',
    ),
    policia(
        'Certificado de supervivencia sin testigos',
        'Certificado policial de supervivencia para el solicitante cuyo domicilio consta en su DNI.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'El domicilio real y efectivo debe constar en el DNI.',
            'Informar nacionalidad, DNI y edad.',
            'Firmar el formulario de solicitud.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/08/Supervivencia-sin-Testigos.pdf',
        fuente='Formulario y condiciones del certificado de supervivencia sin testigos',
    ),
    policia(
        'Certificado de residencia para extranjeros',
        'Certificado policial de residencia para presentar ante la Dirección General de Migraciones.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'Informar nacionalidad, DNI, edad y ocupación.',
            'Aportar el domicilio real y efectivo.',
            'Presentar 2 testigos con DNI, nacionalidad, edad y ocupación.',
            'Los testigos deben tener domicilio en la jurisdicción del requirente.',
            'Firmar el formulario el solicitante y los testigos.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/08/Certificado-de-Residencia-Extrangero.pdf',
        fuente='Formulario y requisitos del certificado de residencia para extranjeros',
    ),
    policia(
        'Constancia policial por extravío',
        'Constancia policial de la pérdida o extravío de un documento u objeto, para presentar ante las autoridades que lo requieran.',
        [
            'Concurrir a la dependencia policial con DNI.',
            'Informar nacionalidad, edad, estado civil y domicilio.',
            'Detallar el documento u objeto extraviado.',
            'Firmar la constancia ante el funcionario policial.',
        ],
        'https://policiamisiones.gob.ar/wp-content/uploads/2024/08/Constancia-Policial.pdf',
        fuente='Formulario y datos exigidos para la constancia policial por extravío',
    ),
])

# ---------------------------------------------------------------------------
# Dirección General de Personas Jurídicas y Registro Público
# ---------------------------------------------------------------------------

PJ_INDEX = 'https://personasjuridicas.misiones.gob.ar/requisitos/'
PJ_MATRICULA = 'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/05/PERSONAS-HUMANAS-QUE-REALIZAN-ACTIVIDAD-ECONOMICA.pdf'
PJ_BENEFICIARIO = 'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/12/DGPJ-BENEFICIARIO-FINAL-06-12-2022.pdf'
PJ_DOMICILIO = 'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2021/08/cambios-de-domicilio.pdf'
PJ_RESERVA = 'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2024/05/Form-Reserva-de-Nombre-2024.docx'
PJ_LIBROS = 'https://personasjuridicas.misiones.gob.ar/wp-content/uploads/2022/09/Modelo-de-Formulario-libros.pdf'


def pj(titulo, descripcion, requisitos, url, *, fuente, destacado=False):
    return _ficha(
        titulo, 'Comercio', 'mixta', 'Posadas', PJ, descripcion, requisitos,
        [('Requisitos y formularios de Personas Jurídicas', url)],
        [
            (PJ_INDEX, 'Índice de requisitos y modelos que enlaza el formulario o instructivo'),
            (url, fuente),
        ],
        SEDES['pj'], destacado,
    )


TRAMITES.extend([
    pj(
        'Matrícula de comerciante',
        'Inscripción de una persona humana que realiza actividad económica en el Registro Público de Comercio.',
        [
            'Nota de presentación con nombre, DNI, CUIL/CUIT, nacionalidad, estado civil, edad, profesión y domicilios particular y comercial.',
            'Indicar el rubro al que se dedicará y aclarar el domicilio fiscal aunque coincida con el particular.',
            'Firma del recurrente certificada ante escribano.',
            'Certificado de antecedentes ante la Jefatura de Policía del interesado.',
            'Constancia de inscripción ante AFIP.',
            'Pago de la tasa administrativa.',
            'Si el rubro es despachante de aduana: copia certificada del título universitario.',
        ],
        PJ_MATRICULA,
        fuente='Requisitos para personas humanas que realizan actividad económica',
        destacado=True,
    ),
    pj(
        'Declaración jurada de beneficiario final',
        'Declaración de las personas humanas que poseen al menos el 10% del capital, derechos de voto o control final de una persona jurídica.',
        [
            'Completar el Anexo I de Declaración Jurada sobre Beneficiario Final.',
            'Informar datos del beneficiario: nombre, documento, CUIT/CUIL/CDI, domicilio, nacionalidad, estado civil, profesión y porcentaje de participación.',
            'Informar datos de la entidad: denominación, matrícula, folio, año y CUIT.',
            'En cadenas de titularidad, describir la cadena hasta la persona humana con control final.',
            'Acompañar estatutos, registros de acciones o participaciones, contratos y transferencias que acrediten la cadena.',
            'Informar toda modificación dentro de los 30 días corridos de producida.',
        ],
        PJ_BENEFICIARIO,
        fuente='Formulario Anexo I, definición, documentación respaldatoria y plazo de actualización',
    ),
    pj(
        'Cambio de domicilio de asociaciones y fundaciones',
        'Actualización del domicilio social de una asociación civil o fundación inscripta en la Dirección de Personas Jurídicas.',
        [
            'Si el estatuto solo indica la localidad: acta de comisión directiva que fija el nuevo domicilio social.',
            'Presentar copia del acta certificada por el Presidente o Secretario.',
            'Acompañar nota comunicando el cambio de domicilio.',
            'Abonar la tasa correspondiente.',
            'Si el estatuto indica un domicilio preciso: convocar Asamblea General Extraordinaria para modificar el artículo 1 del estatuto.',
            'Presentar el acta o testimonio de la asamblea con la nota de cambio de domicilio y el pago de la tasa.',
        ],
        PJ_DOMICILIO,
        fuente='Situaciones, actas y trámite para el cambio de domicilio de asociaciones y fundaciones',
    ),
    pj(
        'Reserva de nombre para sociedades',
        'Verificación de que la denominación que se pretende usar no sea idéntica o similar a otra ya registrada.',
        [
            'Completar el formulario Solicitud de Reserva de Nombre para Sociedades.',
            'Indicar el tipo societario y, si ya está inscripta, la matrícula.',
            'Informar los datos de la persona autorizada para la prosecución del trámite.',
            'Proponer tres opciones de denominación, distintas entre sí y en orden de preferencia, con el tipo societario.',
            'Informar los datos de los socios, con un mínimo de dos salvo sociedades unipersonales.',
            'Abonar la tasa administrativa y presentar en la Dirección de Sociedades Comerciales y Registro Público.',
        ],
        PJ_RESERVA,
        fuente='Formulario de reserva de nombre para sociedades y datos exigidos',
    ),
    pj(
        'Rúbrica de libros societarios',
        'Rúbrica de los libros de actas, diario, IVA, inventario y registro de asistencia a asamblea de una entidad.',
        [
            'Completar el formulario de rúbrica de libros por duplicado.',
            'Informar los datos de la entidad y el domicilio legal.',
            'Informar los datos del autorizado para el trámite: nombre, CUIL/CUIT, domicilio y contacto.',
            'Detallar los libros presentados: actas, diario, IVA compra, IVA venta, inventario y registro de asistencia a asamblea.',
            'Firmar el formulario el presidente de la entidad.',
            'Abonar la tasa administrativa.',
        ],
        PJ_LIBROS,
        fuente='Formulario de rúbrica de libros, datos de la entidad y detalle de libros',
    ),
])

# ---------------------------------------------------------------------------
# Municipalidad de Oberá
# ---------------------------------------------------------------------------

OBERA_GUIA = 'https://www.obera.gob.ar/guia-de-tramites/'


def obera(titulo, descripcion, requisitos, url, *, tema, modalidad='presencial',
          sedes='obera', fuente, destacado=False):
    return _ficha(
        titulo, tema, modalidad, 'Oberá', OBERA, descripcion, requisitos,
        [('Guía de trámites de Oberá', url)],
        [
            (OBERA_GUIA, 'Índice de la guía de trámites municipal'),
            (url, fuente),
        ],
        SEDES[sedes], destacado,
    )


TRAMITES.extend([
    obera(
        'Habilitación comercial con local',
        'Habilitación municipal para abrir un comercio con local en Oberá, según el tipo de personería.',
        [
            'Completar el Formulario 03 de Prefactibilidad.',
            'Persona física: Formulario 03 y 04 completo con sellado de rentas.',
            'Persona física: DNI frente y dorso.',
            'Persona física: constancia de inscripción en AFIP y en Rentas.',
            'Persona física: permiso de ocupación del local comercial.',
            'Persona física: autorización de uso, comodato o contrato de alquiler.',
            'Persona jurídica: Formulario 03 y 05 completo con sellado de rentas.',
            'Persona jurídica: DNI frente y dorso del socio gerente o director.',
            'Persona jurídica: constancias de inscripción en AFIP y Rentas de la sociedad.',
            'Persona jurídica: contrato de constitución social y último pago en caja autónomo del socio gerente.',
            'Persona jurídica: permiso de ocupación y autorización de uso, comodato o alquiler.',
            'Profesionales: título y matrícula del colegio habilitante.',
        ],
        'https://www.obera.gob.ar/habilitacion-comercio-con-local/',
        tema='Comercio',
        modalidad='mixta',
        fuente='Requisitos para personas físicas y jurídicas, formularios y observaciones',
        destacado=True,
    ),
    obera(
        'Habilitación comercial sin local',
        'Habilitación municipal para una actividad comercial que no cuenta con local propio en Oberá.',
        [
            'Persona física: completar el Formulario 1.',
            'Persona física: DNI primera y segunda hoja.',
            'Persona física: constancia de inscripción en AFIP y en Rentas.',
            'Persona física: sellado de rentas.',
            'Persona física: boleta de servicio.',
            'Persona jurídica: completar el Formulario 2.',
            'Persona jurídica: DNI primera y segunda hoja del socio gerente o director.',
            'Persona jurídica: constancias de inscripción en AFIP y Rentas de la sociedad.',
            'Persona jurídica: sellado de rentas.',
            'Persona jurídica: contrato de constitución social.',
            'Persona jurídica: último pago en caja autónomo del socio gerente.',
            'Profesionales: título y matrícula del colegio habilitante.',
        ],
        'https://www.obera.gob.ar/habilitacion-comercio-sin-local/',
        tema='Comercio',
        fuente='Requisitos para personas físicas y jurídicas y formularios descargables',
    ),
    obera(
        'Licencia de conducir por primera vez de 16 a 21 años',
        'Otorgamiento de la licencia nacional de conducir para personas de 16 a 21 años con domicilio en Oberá.',
        [
            'DNI original con domicilio real en Oberá; si se extravió, DNI digital o constancia de inicio del nuevo DNI con foto sellada por el Registro.',
            'Menores de edad: autorización firmada por padres o tutores ante escribano público y partida de nacimiento.',
            'Boleta del CENAT con comprobante de pago; tiene validez de 60 días.',
            'Presentar la boleta impresa en Jujuy 58 para el alta en el sistema nacional y el registro de foto y firma.',
            'Completar el FUT: declaración jurada de afecciones, curso teórico y práctico.',
            'Ficha médica con sello de validez de 30 días.',
            'Presentar DNI, boleta CENAT y FUT aprobado para finalizar la carga y el pago del original.',
        ],
        'https://obera.gob.ar/servicios-municipal/licencia-por-primera-vez-de-16-a-21-anos/',
        tema='Tránsito',
        fuente='Requisitos, plazos y pasos para la primera licencia de 16 a 21 años',
        destacado=True,
    ),
    obera(
        'Licencia de conducir por primera vez para mayores de 21 años',
        'Otorgamiento de la licencia nacional de conducir para personas mayores de 21 años con domicilio en Oberá.',
        [
            'DNI original con domicilio real en Oberá; alternativa: DNI digital o constancia de DNI en trámite con foto sellada.',
            'Boleta del CENAT con comprobante de pago; tiene validez de 60 días.',
            'Presentar la boleta impresa en Jujuy 58 para el alta en el sistema nacional y el registro de foto y firma.',
            'Completar el FUT: declaración jurada de afecciones, curso teórico y práctico.',
            'Ficha médica con sello de validez de 30 días.',
            'Presentar DNI, boleta CENAT y FUT aprobado para finalizar la carga y el pago del original.',
        ],
        'https://obera.gob.ar/servicios-municipal/licencia-por-primera-vez-mas-de-21-anos/',
        tema='Tránsito',
        fuente='Requisitos, plazos y pasos para la primera licencia de mayores de 21 años',
    ),
    obera(
        'Renovación de licencia nacional de conducir',
        'Renovación de la licencia nacional de conducir, con o sin ampliación de categoría, para residentes de Oberá.',
        [
            'DNI original con domicilio real en Oberá.',
            'Licencia Nacional de Conducir vigente.',
            'Boleta del CENAT con comprobante de pago; tiene validez de 60 días.',
            'Presentar la boleta impresa en Jujuy 58 para el alta en el sistema nacional y el FUT.',
            'Ficha médica con sello de validez de 30 días.',
            'Dentro de los 45 días previos al vencimiento no se realiza examen teórico-práctico si no hay infracciones.',
            'Hasta 90 días después del vencimiento: examen teórico. Más de 90 días: examen teórico y práctico.',
            'Categorías D1, D2, D3 y D4: certificado de antecedentes penales RNR.',
        ],
        'https://www.obera.gob.ar/renovacion-licencia-nacional-de-conducir/',
        tema='Tránsito',
        fuente='Requisitos, plazos de renovación y exámenes según vencimiento',
    ),
    obera(
        'Libre deuda de patente del automotor',
        'Certificado municipal que acredita que un vehículo no tiene deudas de patente ni infracciones de tránsito en Oberá.',
        [
            'Verificar que estén canceladas las obligaciones del impuesto automotor y las infracciones de tránsito.',
            'Abonar el derecho de oficina.',
            'Tener el dominio del vehículo.',
            'Puede realizarlo el titular o un gestor, en Jujuy 58, planta baja, o por correo electrónico.',
        ],
        'https://www.obera.gob.ar/solicitud-de-libre-deuda-de-patente/',
        tema='Impuestos',
        modalidad='mixta',
        fuente='Requisitos, responsable y canales de presentación del libre deuda de patente',
    ),
    obera(
        'Libre deuda de inmueble',
        'Certificado municipal que acredita que un inmueble no registra deudas de la tasa inmobiliaria ni del alumbrado público.',
        [
            'Factura o número de partida del inmueble.',
            'Datos del dueño: nombre, apellido y DNI.',
            'Estar al día con la Tasa de Inmueble.',
            'Libre deuda de alumbrado público de CELO.',
        ],
        'https://www.obera.gob.ar/solicitud-de-libre-deuda-inmueble/',
        tema='Impuestos',
        fuente='Requisitos para el libre deuda de inmueble',
    ),
    obera(
        'Carnet sanitario',
        'Certificado de salud para trabajadores de peluquerías, estéticas, institutos de belleza y actividades de tatuajes o perforaciones.',
        [
            'Presentar la ficha médica certificada por un profesional; vence a los 15 días.',
            'Presentar el DNI original.',
            'La foto digital se toma en el mismo lugar y el mismo día del inicio.',
            'El trámite es personal y se inicia en la oficina de Seguridad Alimentaria, Bolivia 530.',
            'El carnet tiene vigencia de 1 año.',
        ],
        'https://www.obera.gob.ar/carnet-sanitario/',
        tema='Salud',
        sedes='obera_carnet',
        fuente='Requisitos, vigencia y sede del carnet sanitario',
    ),
    obera(
        'Castración de mascotas',
        'Turno para la esterilización quirúrgica gratuita de mascotas de vecinos con domicilio en Oberá.',
        [
            'Ser mayor de edad.',
            'Presentar DNI.',
            'Tener domicilio real en el ejido municipal de Oberá.',
            'Solicitar turno telefónico los lunes de 6:30 a 8:30 al 3755 400798.',
        ],
        'https://www.obera.gob.ar/esterilizacion-quirurgica-de-mascotas/',
        tema='Ambiente',
        sedes='obera_castracion',
        fuente='Requisitos, turnos y sede para la castración de mascotas',
    ),
])

# ---------------------------------------------------------------------------
# Municipalidad de Puerto Iguazú
# ---------------------------------------------------------------------------

IGUAZU_TRANSITO = 'https://www.iguazu.gob.ar/tramites-de-transito/'
IGUAZU_BROMATOLOGIA = 'https://www.iguazu.gob.ar/tramites-de-bromatologia/'
IGUAZU_FISCALIZACION = 'https://www.iguazu.gob.ar/tramites-de-fiscalizacion/'
IGUAZU_HABILITACION = 'https://www.iguazu.gob.ar/solicitud-de-habilitacion-e-inscripcion-o-traslado/'
IGUAZU_LIBRETA = 'https://www.iguazu.gob.ar/libreta-sanitaria/'
IGUAZU_ANEXO = 'https://www.iguazu.gob.ar/anexo-examen-medico/'


def iguazu(titulo, descripcion, requisitos, url, *, tema, fuentes,
           modalidad='presencial', destacado=False):
    return _ficha(
        titulo, tema, modalidad, 'Puerto Iguazú', IGUAZU, descripcion,
        requisitos,
        [('Guía o formulario oficial de Puerto Iguazú', url)],
        list(fuentes),
        SEDES['iguazu'], destacado,
    )


TRAMITES.extend([
    iguazu(
        'Licencia de conducir por primera vez para mayores de edad',
        'Otorgamiento de la licencia nacional de conducir en Puerto Iguazú, con curso y exámenes obligatorios.',
        [
            'Fotocopia del DNI, ambos lados, con domicilio en Puerto Iguazú.',
            'Asistir al curso de capacitación.',
            'Rendir el examen teórico del Manual del Conductor.',
            'Rendir el examen práctico de manejo.',
            'Realizar el examen psicofísico.',
            'La licencia tarda de 4 a 5 días hábiles en tramitarse.',
        ],
        IGUAZU_TRANSITO,
        tema='Tránsito',
        fuentes=[
            (IGUAZU_TRANSITO, 'Requisitos y plazos del otorgamiento de licencia para mayores de edad'),
        ],
        destacado=True,
    ),
    iguazu(
        'Licencia de conducir por primera vez para menores de 16 y 17 años',
        'Otorgamiento de la licencia nacional de conducir para menores de edad, con autorización de sus representantes.',
        [
            'Fotocopia del DNI, ambos lados, con domicilio en Puerto Iguazú.',
            'Acta de nacimiento autorizada por juzgado o escribanía.',
            'Presencia de los padres.',
            'Autorización del representante legal conforme al Art. 11 de la Ley 24.449.',
            'Cumplir el curso de capacitación y los exámenes teórico, práctico y psicofísico del otorgamiento.',
        ],
        IGUAZU_TRANSITO,
        tema='Tránsito',
        fuentes=[
            (IGUAZU_TRANSITO, 'Requisitos y autorización para licencia de menores de edad'),
        ],
    ),
    iguazu(
        'Renovación de licencia de conducir',
        'Renovación de la licencia nacional de conducir de Puerto Iguazú, antes o después del vencimiento.',
        [
            'Fotocopia del DNI, ambos lados, con domicilio en Puerto Iguazú.',
            'Carnet anterior o vencido.',
            'La licencia puede renovarse antes de la fecha de vencimiento.',
            'Si cambió de domicilio, debe acreditar domicilio en Puerto Iguazú o presentar constancia de DNI en trámite.',
        ],
        IGUAZU_TRANSITO,
        tema='Tránsito',
        fuentes=[
            (IGUAZU_TRANSITO, 'Requisitos, plazos y condiciones de la renovación de licencia'),
        ],
    ),
    iguazu(
        'Ampliación de categoría de licencia de conducir',
        'Ampliación de la categoría de la licencia nacional de conducir en Puerto Iguazú.',
        [
            'Fotocopia del DNI, ambos lados, con domicilio en Puerto Iguazú.',
            'Carnet anterior o vencido.',
            'Para las clases C, D y E se debe haber obtenido la clase B al menos un año antes.',
            'Las licencias profesionales se otorgan por un período máximo de 2 años.',
        ],
        IGUAZU_TRANSITO,
        tema='Tránsito',
        fuentes=[
            (IGUAZU_TRANSITO, 'Requisitos y antigüedad para ampliar la categoría de licencia'),
        ],
    ),
    iguazu(
        'Duplicado o triplicado de licencia de conducir',
        'Emisión de un duplicado o triplicado de la licencia por extravío o actualización de datos.',
        [
            'Fotocopia del DNI, ambos lados, con domicilio en Puerto Iguazú.',
            'Constancia policial de extravío.',
            'Abonar $423,40 por duplicado o actualización de datos.',
        ],
        IGUAZU_TRANSITO,
        tema='Tránsito',
        fuentes=[
            (IGUAZU_TRANSITO, 'Requisitos y costo del duplicado o actualización de licencia'),
        ],
    ),
    iguazu(
        'Libreta sanitaria por primera vez',
        'Libreta sanitaria para trabajadores de actividades con riesgo de transmisión de enfermedades alimentarias.',
        [
            'Examen médico completo: clínico y bioquímico.',
            'Fotocopia del DNI, ambos lados.',
            'Constancia de domicilio si el DNI no tiene el domicilio real.',
            'Una foto tipo carnet de 4x4.',
            'Curso de BPM, POES y MIP optativo; el examen es obligatorio.',
            'Completar el anexo de examen médico con los resultados clínicos y de laboratorio.',
        ],
        IGUAZU_BROMATOLOGIA,
        tema='Salud',
        fuentes=[
            (IGUAZU_BROMATOLOGIA, 'Requisitos de la libreta sanitaria por primera vez'),
            (IGUAZU_LIBRETA, 'Formulario de libreta sanitaria: datos del trabajador, otorgamiento y vencimiento'),
            (IGUAZU_ANEXO, 'Anexo de examen médico: exámenes clínicos y de laboratorio'),
        ],
    ),
    iguazu(
        'Renovación de libreta sanitaria',
        'Renovación de la libreta sanitaria de Puerto Iguazú con nuevo examen médico.',
        [
            'Examen médico completo: clínico y bioquímico.',
            'Libreta sanitaria anterior.',
            'Curso de BPM, POES y MIP optativo; el examen es obligatorio.',
            'Completar el anexo de examen médico con los resultados clínicos y de laboratorio.',
        ],
        IGUAZU_BROMATOLOGIA,
        tema='Salud',
        fuentes=[
            (IGUAZU_BROMATOLOGIA, 'Requisitos de la renovación de la libreta sanitaria'),
            (IGUAZU_LIBRETA, 'Formulario de libreta sanitaria: datos de renovación y vencimiento'),
            (IGUAZU_ANEXO, 'Anexo de examen médico para la renovación'),
        ],
    ),
    iguazu(
        'Habilitación e inscripción o traslado de comercio',
        'Habilitación municipal de una actividad comercial en Puerto Iguazú, para personas físicas o jurídicas.',
        [
            'Completar la Solicitud de Habilitación e Inscripción o Traslado con ramo principal, ramos anexos, nombre del negocio, CUIT y domicilio.',
            'Persona física: copia del DNI del titular o representante legal con domicilio en Puerto Iguazú.',
            'Persona física: comprobante de inscripción en DGR y AFIP con domicilio en Puerto Iguazú, o constancia de puntos de venta y domicilios.',
            'Persona física: manifestación de bienes certificada por Contador Público Nacional.',
            'Persona física: título de propiedad o contrato de locación con manzana, lote y partida, firmas certificadas y sellado por DGR.',
            'Persona física: certificado de domicilio comercial.',
            'Persona jurídica: contrato social o estatuto inscripto en el Registro Público de Comercio.',
            'Persona jurídica: último balance o balance inicial certificado por Contador Público Nacional.',
            'Persona jurídica: acta de designación de autoridades y, si corresponde, acta de instalación de la sucursal en Puerto Iguazú.',
            'Persona jurídica: fijar domicilio fiscal en Puerto Iguazú.',
            'Si actúa un apoderado: acreditar la personería con poder notarial.',
            'Una vez obtenida la habilitación, inscribirse en el Registro de Comercio Interior en Av. Victoria Aguirre 396.',
        ],
        IGUAZU_HABILITACION,
        tema='Comercio',
        fuentes=[
            (IGUAZU_FISCALIZACION, 'Índice de trámites de fiscalización que enlaza la solicitud de habilitación'),
            (IGUAZU_HABILITACION, 'Formulario y documentación exigida para personas físicas y jurídicas'),
        ],
    ),
])
