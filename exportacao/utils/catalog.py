"""Singleton por processo; armazena classes, nunca dados de requisições."""

from threading import Lock, RLock


class CatalogoExportadores:
    _instancia = None
    _criacao_lock = Lock()

    def __new__(cls):
        with cls._criacao_lock:
            if cls._instancia is None:
                instancia = super().__new__(cls)
                instancia._registro = {}
                instancia._registro_lock = RLock()
                cls._instancia = instancia
            return cls._instancia

    def registrar(self, formato, criador_cls, familia_cls=None):
        with self._registro_lock:
            self._registro[formato] = (criador_cls, familia_cls)

    def resolver(self, formato):
        with self._registro_lock:
            try:
                return self._registro[formato]
            except KeyError as exc:
                raise ValueError(f"Formato de exportação '{formato}' não suportado.") from exc
