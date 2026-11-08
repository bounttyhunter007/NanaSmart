from .base_exporter import Exportador
from .creators import CriadorExportador

class ExportadorFactory:
    """Resolve o criador pelo formato e delega a criação ao Factory Method."""

    _registro = {}

    @classmethod
    def registrar(cls, formato: str, criador_cls: type[CriadorExportador]):
        if not isinstance(criador_cls, type) or not issubclass(criador_cls, CriadorExportador):
            raise TypeError("O criador registrado deve herdar de CriadorExportador.")
        cls._registro[formato] = criador_cls

    @classmethod
    def criar(cls, formato: str) -> Exportador:
        criador_cls = cls._registro.get(formato)
        if not criador_cls:
            raise ValueError(f"Formato de exportação '{formato}' não suportado.")
        return criador_cls().criar_exportador()
