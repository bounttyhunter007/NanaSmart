from abc import ABC, abstractmethod

from .base_exporter import Exportador
from .csv_exporter import ExportadorCSV
from .excel_exporter import ExportadorExcel
from .pdf_exporter import ExportadorPDF


class CriadorExportador(ABC):
    """Creator do Factory Method para uma família de exportadores."""

    @abstractmethod
    def criar_exportador(self) -> Exportador:
        """Cria o exportador escolhido pelo criador concreto."""
        raise NotImplementedError


class CriadorExportadorCSV(CriadorExportador):
    def criar_exportador(self) -> ExportadorCSV:
        return ExportadorCSV()


class CriadorExportadorExcel(CriadorExportador):
    def criar_exportador(self) -> ExportadorExcel:
        return ExportadorExcel()


class CriadorExportadorPDF(CriadorExportador):
    def criar_exportador(self) -> ExportadorPDF:
        return ExportadorPDF()
