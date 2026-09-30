"""Requerimientos no funcionales que se comprueban con un test.

De los 11 RNF del documento, varios ya estaban cubiertos por las pruebas
de roles, acceso, privacidad y chat (esos quedan en la tabla de
trazabilidad del README). Este archivo agrega los dos que todavía no
tenían evidencia escrita:

  * **RNF-03 Rendimiento**: el listado no hace una consulta por fila
    (N+1) y el índice del asistente no se reconstruye en cada pregunta.
  * **RNF-05 Integridad**: la base rechaza duplicados y protege los
    datos referenciados.

Los tests no cronometran (los tiempos vuelan y una máquina lenta no es
un bug): miden lo que sí es estable, que es la cantidad de consultas a
la base.
"""

from unittest import mock

from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from munitramites.models import Municipio, Requisito
from munitramites.services.chatbot import indexar, responder

from .base import TestCase, municipio, tramite


class RendimientoTests(TestCase):
    """RNF-03: responder en un tiempo razonable, sin demoras innecesarias."""

    def _queries_del_listado(self):
        """GET /tramites/ y cuántas consultas a la base le costó."""
        with CaptureQueriesContext(connection) as ctx:
            respuesta = self.client.get(reverse('tramites'))
        self.assertEqual(respuesta.status_code, 200)
        return len(ctx)

    def test_listado_no_hace_un_query_por_tramite(self):
        """Si crecen los trámites, no crecen las consultas (anti N+1)."""
        for i in range(3):
            tramite(titulo=f'Tramite de prueba {i}')
        con_pocos = self._queries_del_listado()

        for i in range(4, 15):
            tramite(titulo=f'Tramite de prueba {i}')
        con_muchos = self._queries_del_listado()

        self.assertLessEqual(
            con_muchos, con_pocos,
            f'El listado hizo {con_muchos} consultas con 15 trámites y '
            f'{con_pocos} con 3: creció con los datos (N+1).',
        )

    def test_el_indice_no_se_reconstruye_en_cada_pregunta(self):
        """La base se lee una vez; después el BM25 trabaja en memoria."""
        tramite()
        responder('renovacion de DNI')   # calienta el índice

        with mock.patch.object(
            indexar, '_construir', wraps=indexar._construir
        ) as construir:
            responder('partida de nacimiento')

        construir.assert_not_called()


class IntegridadTests(TestCase):
    """RNF-05: los datos quedan consistentes y no se pierden."""

    def test_no_se_puede_repetir_el_nombre_de_un_municipio(self):
        municipio('Posadas')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Municipio.objects.create(nombre='Posadas')

    def test_no_se_pueden_dos_requisitos_en_el_mismo_orden(self):
        t = tramite()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Requisito.objects.create(
                    tramite=t, orden=1, descripcion='Requisito duplicado'
                )

    def test_no_se_puede_borrar_un_municipio_con_tramites(self):
        """`PROTECT` en la FK: borrar la localidad no se lleva los
        trámites que cuelgan de ella."""
        t = tramite()

        with self.assertRaises(ProtectedError):
            with transaction.atomic():
                t.municipio.delete()

    def test_al_borrar_el_tramite_no_quedan_requisitos_huerfanos(self):
        """`CASCADE` en la FK interna: el trámite y sus requisitos van
        juntos y no queda basura en la tabla."""
        t = tramite()
        tramite_id = t.pk
        self.assertEqual(Requisito.objects.filter(tramite_id=tramite_id).count(), 1)

        t.delete()

        self.assertEqual(
            Requisito.objects.filter(tramite_id=tramite_id).count(), 0
        )
