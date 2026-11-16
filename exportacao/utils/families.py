"""Abstract Factory: gera o exportador e os metadados da mesma família."""

from abc import ABC, abstractmethod

from .base_exporter import Exportador
from .creators import CriadorExportadorCSV, CriadorExportadorExcel, CriadorExportadorPDF
from .download_metadata import MetadadosDownload, MetadadosCSV, MetadadosExcel, MetadadosPDF


class FabricaFamiliaExportacao(ABC):
    @abstractmethod
    def criar_exportador(self) -> Exportador:
        raise NotImplementedError

    @abstractmethod
    def criar_metadados(self) -> MetadadosDownload:
        raise NotImplementedError


class FamiliaCSV(FabricaFamiliaExportacao):
    def criar_exportador(self) -> Exportador:
        return CriadorExportadorCSV(self.criar_metadados()).criar_exportador()

    def criar_metadados(self) -> MetadadosDownload:
        return MetadadosCSV()


class FamiliaExcel(FabricaFamiliaExportacao):
    def criar_exportador(self) -> Exportador:
        return CriadorExportadorExcel(self.criar_metadados()).criar_exportador()

    def criar_metadados(self) -> MetadadosDownload:
        return MetadadosExcel()


class FamiliaPDF(FabricaFamiliaExportacao):
    def criar_exportador(self) -> Exportador:
        return CriadorExportadorPDF(self.criar_metadados()).criar_exportador()

    def criar_metadados(self) -> MetadadosDownload:
        return MetadadosPDF()
