from .base_exporter import Exportador
from .creators import CriadorExportador
from .catalog import CatalogoExportadores
from .decorators import ExportadorComLog
from .families import FabricaFamiliaExportacao

class ExportadorFactory:
    """Seleciona a família no catálogo e entrega o exportador decorado."""

    @classmethod
    def registrar(cls, formato: str, criador_cls: type[CriadorExportador], *, familia_cls=None):
        if not isinstance(criador_cls, type) or not issubclass(criador_cls, CriadorExportador):
            raise TypeError("O criador registrado deve herdar de CriadorExportador.")
        if familia_cls is not None and (
            not isinstance(familia_cls, type) or not issubclass(familia_cls, FabricaFamiliaExportacao)
        ):
            raise TypeError("A família deve herdar de FabricaFamiliaExportacao.")
        CatalogoExportadores().registrar(formato, criador_cls, familia_cls)

    @classmethod
    def criar(cls, formato: str) -> Exportador:
        criador_cls, familia_cls = CatalogoExportadores().resolver(formato)
        if familia_cls is None:
            # Mantém a extensão antiga que registra somente um criador.
            exportador = criador_cls().criar_exportador()
        else:
            exportador = familia_cls().criar_exportador()
        return ExportadorComLog(exportador)
