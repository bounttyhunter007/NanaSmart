"""Iterator próprio sobre a consulta de leituras, sem carregar toda a coleção."""

from collections.abc import Iterator


class IteradorLeituras(Iterator):
    def __init__(self, queryset, *, chunk_size=500):
        self._leituras = iter(queryset.iterator(chunk_size=chunk_size))

    def __iter__(self):
        return self

    def __next__(self):
        # Ordem, filtros e valores pertencem à consulta e ao serviço de análise.
        return next(self._leituras)
