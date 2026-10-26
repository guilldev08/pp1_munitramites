# -*- coding: utf-8 -*-
"""Requisitos normalizados: Policía de Misiones."""

REQUISITOS = {
    'Certificado de convivencia': [
        'DNI',
        'Domicilio real y efectivo y fecha de inicio de la convivencia',
        'Datos de la persona con quien convive: nombre, tipo y número de documento y vínculo',
        'Dos testigos con DNI y domicilio',
        'Formulario firmado por el solicitante y los testigos',
    ],
    'Certificado de domicilio con testigos': [
        'DNI',
        'Datos personales: nacionalidad, número de DNI, edad y ocupación',
        'Domicilio real y efectivo que se certificará',
        'Dos testigos con DNI y domicilio declarado',
        'Formulario firmado por el solicitante y ambos testigos',
    ],
    'Certificado de domicilio sin testigos': [
        'DNI',
        'Domicilio declarado que conste en el DNI',
        'Datos personales: nacionalidad, número de DNI, edad y ocupación',
        'Formulario de solicitud firmado',
    ],
    'Certificado de residencia para extranjeros': [
        'DNI',
        'Datos personales: nacionalidad, DNI, edad y ocupación',
        'Domicilio real y efectivo',
        'Dos testigos con DNI, nacionalidad, edad y ocupación',
        'Testigos con domicilio en la jurisdicción del requirente',
        'Formulario firmado por el solicitante y los testigos',
    ],
    'Certificado de supervivencia con testigos': [
        'DNI',
        'Datos personales: nacionalidad, DNI, edad y domicilio real y efectivo',
        'Dos testigos con DNI, nacionalidad y edad, o un apoderado',
        'Formulario firmado por el solicitante, los testigos o el apoderado',
    ],
    'Certificado de supervivencia sin testigos': [
        'DNI',
        'Domicilio real y efectivo que conste en el DNI',
        'Datos personales: nacionalidad, DNI y edad',
        'Formulario de solicitud firmado',
    ],
    'Constancia policial por extravío': [
        'DNI',
        'Datos personales: nacionalidad, edad, estado civil y domicilio',
        'Detalle del documento u objeto extraviado',
        'Firma de la constancia ante el funcionario policial',
    ],
}
