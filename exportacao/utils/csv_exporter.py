"""
Utilitário para exportação de dados em formato CSV.
"""
import csv
from django.http import HttpResponse
from .base_exporter import Exportador

class ExportadorCSV(Exportador):
    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        """
        Gera um HttpResponse com conteúdo CSV pronto para download.
        """
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{nome}.csv"'

        # BOM para Excel reconhecer acentos corretamente
        response.write('\ufeff')

        writer = csv.writer(response, delimiter=';')
        writer.writerow(colunas)

        for linha in linhas:
            writer.writerow(linha)

        return response
