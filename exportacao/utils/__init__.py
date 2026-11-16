from .exporter_factory import ExportadorFactory
from .creators import (
    CriadorExportadorCSV,
    CriadorExportadorExcel,
    CriadorExportadorPDF,
)

ExportadorFactory.registrar('csv', CriadorExportadorCSV)
ExportadorFactory.registrar('excel', CriadorExportadorExcel)
ExportadorFactory.registrar('pdf', CriadorExportadorPDF)

__all__ = ['ExportadorFactory']
