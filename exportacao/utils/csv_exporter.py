"""
Utilitário para exportação de dados em formato CSV.
"""
import csv
from django.http import HttpResponse
from .base_exporter import Exportador
from .download_metadata import MetadadosCSV

class ExportadorCSV(Exportador):
    def __init__(self, metadados=None):
        self._metadados = metadados if metadados is not None else MetadadosCSV()

    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        """
        Gera um HttpResponse com conteúdo CSV pronto para download.
        """
        response = self._metadados.aplicar(HttpResponse(), nome)

        # BOM para Excel reconhecer acentos corretamente
        response.write('\ufeff')

        writer = csv.writer(response, delimiter=';')
        writer.writerow(colunas)

        for linha in linhas:
            writer.writerow(linha)

        return response
