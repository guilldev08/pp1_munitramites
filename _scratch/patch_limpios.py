# -*- coding: utf-8 -*-
"""Ajustes puntuales de redacción después de la primera aplicación."""

from munitramites.models import Requisito, Tramite

CAMBIOS = [
    (
        'Inicio de trámite de obra en el sistema GOP',
        'Usuario propio y del profesional autorizado registrados en el sistema GOP',
        'Usuario propio y del profesional autorizado habilitados para el registro de la obra',
    ),
    (
        'Denuncia de venta del automotor',
        'Formulario de denuncia de venta o constancia online',
        'Formulario de denuncia de venta o constancia digital',
    ),
    (
        'Construyo Mi Casa',
        'Titular menor de 60 años',
        'Titular de hasta 60 años',
    ),
    (
        'Construyo Mi Casa',
        'Acta de matrimonio o certificado de unión convivencial; certificado de convivencia policial si está en trámite',
        'Acta de matrimonio o certificado de unión convivencial; certificado de convivencia policial si la unión convivencial está en curso',
    ),
    (
        'Construyo Mi Casa',
        'Persona divorciada: sentencia de divorcio; disolución del grupo familiar anterior: sentencia o constancia de trámite iniciado',
        'Persona divorciada: sentencia de divorcio; disolución del grupo familiar anterior: sentencia o constancia de inicio del expediente',
    ),
    (
        'Reserva de nombre para sociedades',
        'Datos de la persona autorizada para la prosecución del trámite',
        'Datos de la persona autorizada para la prosecución de la solicitud',
    ),
    (
        'Rúbrica de libros societarios',
        'Datos del autorizado para el trámite: nombre, CUIL/CUIT, domicilio y contacto',
        'Datos del autorizado: nombre, CUIL/CUIT, domicilio y contacto',
    ),
    (
        'Constancia de servicio de agua y/o cloaca',
        'Pago del costo según el código de facturación',
        'Pago del costo según la categoría de facturación',
    ),
    (
        'Inscripción de matrimonio',
        'Libreta de matrimonio civil y pago de las tasas respectivas',
        'Libreta de matrimonio civil, si corresponde, y pago de las tasas respectivas',
    ),
    (
        'Unión convivencial',
        'DNI de ambos contrayentes con el mismo domicilio; constancia de DNI en trámite aceptada',
        'DNI de ambos contrayentes con el mismo domicilio; constancia de DNI en curso aceptada',
    ),
    (
        'Unión convivencial',
        'Formulario de unión convivencial impreso y presentado',
        'Formulario de unión convivencial',
    ),
    (
        'Habilitación de servicio de radiodiagnóstico y equipos emisores de radiaciones',
        'Nota modelo de inicio de trámite dirigida a la Dirección de Saneamiento Ambiental',
        'Nota modelo de solicitud dirigida a la Dirección de Saneamiento Ambiental',
    ),
    (
        'Renovación de habilitación de equipos de rayos X, RMI y otros',
        'Nota modelo de inicio de trámite',
        'Nota modelo de solicitud',
    ),
    (
        'Habilitación comercial con local',
        'Persona jurídica: contrato constitutivo y último pago en caja autónomo del socio gerente',
        'Persona jurídica: contrato constitutivo y último pago en la Caja de Autónomos del socio gerente',
    ),
    (
        'Habilitación comercial sin local',
        'Persona jurídica: último pago en caja autónomo del socio gerente',
        'Persona jurídica: último pago en la Caja de Autónomos del socio gerente',
    ),
    (
        'Renovación de licencia de conducir',
        'Acreditación de domicilio en Puerto Iguazú o constancia de DNI en trámite, si cambió de domicilio',
        'Acreditación de domicilio en Puerto Iguazú o constancia de DNI en curso, si cambió de domicilio',
    ),
]

DESCRIPCIONES = {
    'Alta de Certificado Fiscal para Contratar': (
        'Solicitud de alta del certificado que permite contratar con el Estado provincial.'
    ),
    'Emisión de Certificado Fiscal para Contratar': (
        'Emisión del certificado fiscal para contratar a partir de un Certificado Fiscal para Contratar vigente.'
    ),
    'Certificación para inicio de comodato precario': (
        'Certificado municipal para el comodato precario de un inmueble.'
    ),
    'Cambio de domicilio en el DNI': (
        'Actualización de la dirección que figura en el DNI.'
    ),
    'Nuevo ejemplar de DNI': (
        'Solicitud de un nuevo ejemplar del Documento Nacional de Identidad.'
    ),
    'Solicitud de actas legalizadas': (
        'Solicitud de actas de nacimiento, matrimonio o defunción legalizadas de la provincia de Misiones.'
    ),
    'Actualización de DNI de 5 a 8 años': (
        'Actualización del DNI para niños y niñas de 5 a 8 años.'
    ),
}

for titulo, viejo, nuevo in CAMBIOS:
    encontrados = Requisito.objects.filter(
        tramite__titulo=titulo, descripcion=viejo
    )
    if encontrados.count() != 1:
        raise SystemExit(
            f'Se esperaba un requisito en «{titulo}» con «{viejo}», '
            f'pero hay {encontrados.count()}.'
        )
    encontrados.update(descripcion=nuevo)
    print(f'Requisito actualizado: {titulo}')

for titulo, descripcion in DESCRIPCIONES.items():
    tramite = Tramite.objects.get(titulo=titulo)
    tramite.descripcion = descripcion
    tramite.save(update_fields=['descripcion', 'actualizado'])
    print(f'Descripción actualizada: {titulo}')

print('Listo.')
