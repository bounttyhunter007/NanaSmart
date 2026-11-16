from .exporter_factory import ExportadorFactory
from .creators import (
    CriadorExportadorCSV,
    CriadorExportadorExcel,
    CriadorExportadorPDF,
)
from .families import FamiliaCSV, FamiliaExcel, FamiliaPDF

ExportadorFactory.registrar('csv', CriadorExportadorCSV, familia_cls=FamiliaCSV)
ExportadorFactory.registrar('excel', CriadorExportadorExcel, familia_cls=FamiliaExcel)
ExportadorFactory.registrar('pdf', CriadorExportadorPDF, familia_cls=FamiliaPDF)

__all__ = ['ExportadorFactory']
