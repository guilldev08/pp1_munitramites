# -*- coding: utf-8 -*-
"""Requisitos normalizados: ATM."""

TITULOS = {
    'Alta de Certificado Fiscal para Contratar (SR345)': 'Alta de Certificado Fiscal para Contratar',
    'Alta, modificación o cese de actividades (SR311)': 'Alta, modificación o cese de actividades',
    'Cambio de titular o contribuyente inmobiliario (SR308)': 'Cambio de titular o contribuyente inmobiliario',
    'Certificado de libre deuda inmobiliario (SR309)': 'Certificado de libre deuda inmobiliario',
    'Constancia de cumplimiento de obligaciones fiscales (SR322)': 'Constancia de cumplimiento de obligaciones fiscales',
    'Declaración Jurada anual de Ingresos Brutos (SR320)': 'Declaración Jurada anual de Ingresos Brutos',
    'Declaración Jurada mensual de Ingresos Brutos (SR318)': 'Declaración Jurada mensual de Ingresos Brutos',
    'Declaración Jurada mensual de agente de percepción (SR129)': 'Declaración Jurada mensual de agente de percepción',
    'Declaración Jurada mensual de agente de retención (SR128)': 'Declaración Jurada mensual de agente de retención',
    'Declaración Jurada mensual de pagos a cuenta (SR343)': 'Declaración Jurada mensual de pagos a cuenta',
    'Emisión de Certificado Fiscal para Contratar (SR348)': 'Emisión de Certificado Fiscal para Contratar',
    'Exclusiones, compensaciones y devoluciones (SF178)': 'Exclusiones, compensaciones y devoluciones',
    'Solicitud de exención de Sellos (SR352)': 'Solicitud de exención de Sellos',
}

REQUISITOS = {
    'Alta de Certificado Fiscal para Contratar (SR345)': [
        'CUIT y clave fiscal Nivel 2',
        'Inscripción en Ingresos Brutos',
    ],
    'Alta, modificación o cese de actividades (SR311)': [
        'Formulario de alta, modificación o cese de actividades, con el motivo correspondiente',
        'Documentación del Legajo Único',
    ],
    'Cambio de nivel de clave fiscal': [
        'Clave fiscal Nivel 1',
        'Documentación del Artículo 5 de la RG 14/2023 por Legajo Único',
    ],
    'Cambio de titular o contribuyente inmobiliario (SR308)': [
        'CUIT y Clave de Identificación Tributaria',
        'Documentación que acredite la titularidad: cesión de derechos, boleto de compraventa, adjudicación de EBY o IPRODHA, permiso de ocupación, título de propiedad o sentencia judicial por usucapión',
    ],
    'Certificado de libre deuda inmobiliario (SR309)': [
        'CUIT y Clave de Identificación Tributaria',
        'Solicitud presentada por escribano, abogado o martillero',
    ],
    'Constancia de cumplimiento de obligaciones fiscales (SR322)': [
        'CUIT y clave fiscal Nivel 2',
        'Inscripción en Ingresos Brutos',
        'Facturación superior a $250.000',
    ],
    'Declaración Jurada anual de Ingresos Brutos (SR320)': [
        'Clave fiscal Nivel 2',
        'Inscripción en Ingresos Brutos',
        'Declaraciones juradas mensuales presentadas sin observaciones',
    ],
    'Declaración Jurada mensual de Ingresos Brutos (SR318)': [
        'Inscripción como contribuyente directo en Ingresos Brutos',
        'CUIT y Clave de Identificación Tributaria',
    ],
    'Declaración Jurada mensual de agente de percepción (SR129)': [
        'Inscripción como contribuyente en el impuesto',
        'CUIT y Clave de Identificación Tributaria',
    ],
    'Declaración Jurada mensual de agente de retención (SR128)': [
        'Inscripción como contribuyente en el impuesto',
        'CUIT y Clave de Identificación Tributaria',
    ],
    'Declaración Jurada mensual de pagos a cuenta (SR343)': [
        'Inscripción como contribuyente en el impuesto',
        'CUIT y Clave de Identificación Tributaria',
    ],
    'Emisión de Certificado Fiscal para Contratar (SR348)': [
        'CUIT y clave fiscal Nivel 2',
        'Inscripción en Ingresos Brutos',
        'Certificado Fiscal para Contratar vigente',
    ],
    'Exclusiones, compensaciones y devoluciones (SF178)': [
        'Clave fiscal y Domicilio Fiscal Electrónico',
        'Motivo de la solicitud: exclusión, reducción, compensación, cesión, devolución o reintegro',
        'Documentación respaldatoria en PDF, máximo 5 MB',
    ],
    'Solicitud de exención de Sellos (SR352)': [
        'Clave fiscal Nivel 2',
        'Domicilio Fiscal Electrónico',
        'Documentación en PDF, máximo 5 MB',
    ],
}
