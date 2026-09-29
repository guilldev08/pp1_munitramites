"""Etapa 1 — INDEXAR: convertir los trámites en fragmentos recuperables.

El índice es una lista plana de `Fragmento`. Cada fragmento guarda de dónde
vino (`tramite_id`) para que la respuesta siempre pueda CITAR LA FUENTE.

    ficha      → título + descripción + tema + modalidad + municipio + organismo
    requisito  → un fragmento por requisito, con el título del trámite

El índice se construye una vez y se guarda en memoria; cualquier alta o
edición de un trámite, requisito, municipio u organismo lo invalida
(`conectar_senales`). Si mañana el sitio crece, este modulo es el unico que
hay que tocar para reemplazarlo por un indice externo (pgvector, FAISS…).
"""

from dataclasses import dataclass

from ...models import Municipio, Organismo, Requisito, Tramite

__all__ = ['Fragmento', 'conectar_senales', 'invalidar', 'obtener_indice']


@dataclass(frozen=True)
class Fragmento:
    """Un pedazo de conocimiento con su fuente."""

    id: str
    tramite_id: int
    tramite_titulo: str
    tipo: str      # 'ficha' | 'requisito'
    texto: str     # texto crudo que se indexa


def _construir():
    """Recorre los tramites activos y arma los fragmentos."""
    tramites = (
        Tramite.objects.filter(activo=True)
        .select_related('municipio', 'organismo')
        .prefetch_related('requisitos')
    )

    fragmentos = []
    for t in tramites:
        fragmentos.append(Fragmento(
            id=f't{t.pk}',
            tramite_id=t.pk,
            tramite_titulo=t.titulo,
            tipo='ficha',
            texto=(
                f'{t.titulo}. {t.descripcion} '
                f'Tema: {t.get_tema_display()}. '
                f'Modalidad: {t.get_modalidad_display()}. '
                f'Municipio: {t.municipio.nombre}. '
                f'Organismo responsable: {t.organismo.nombre}. '
                f'Requisitos: '
                + '; '.join(r.descripcion for r in t.requisitos.all()) + '.'
            ),
        ))
        for r in t.requisitos.all():
            fragmentos.append(Fragmento(
                id=f't{t.pk}r{r.pk}',
                tramite_id=t.pk,
                tramite_titulo=t.titulo,
                tipo='requisito',
                texto=f'Requisito de {t.titulo}: {r.descripcion}.',
            ))
    return fragmentos


# Cache por proceso. Se invalida con señales (ver conectar_senales).
_cache = None


def obtener_indice():
    """Devuelve el índice (construyéndolo si hace falta)."""
    global _cache
    if _cache is None:
        _cache = _construir()
    return _cache


def invalidar(*_args, **_kwargs):
    """Deja el índice vacío para que se reconstruya en el próximo uso."""
    global _cache
    _cache = None


def conectar_senales():
    """Se engancha a los cambios de datos (se llama desde apps.ready())."""
    from django.db.models.signals import post_delete, post_save

    for modelo in (Tramite, Requisito, Municipio, Organismo):
        post_save.connect(
            invalidar, sender=modelo, dispatch_uid=f'indice_save_{modelo.__name__}'
        )
        post_delete.connect(
            invalidar, sender=modelo, dispatch_uid=f'indice_del_{modelo.__name__}'
        )
