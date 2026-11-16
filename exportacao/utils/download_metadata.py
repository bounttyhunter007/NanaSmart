"""Segundo produto das famílias de exportação: contrato do arquivo baixado."""

from abc import ABC, abstractmethod


class MetadadosDownload(ABC):
    @abstractmethod
    def aplicar(self, response, nome):
        """Aplica MIME e nome do arquivo à resposta já gerada."""
        raise NotImplementedError

    def _aplicar(self, response, nome, content_type, extensao):
        response['Content-Type'] = content_type
        response['Content-Disposition'] = f'attachment; filename="{nome}.{extensao}"'
        return response


class MetadadosCSV(MetadadosDownload):
    def aplicar(self, response, nome):
        return self._aplicar(response, nome, 'text/csv; charset=utf-8', 'csv')


class MetadadosExcel(MetadadosDownload):
    def aplicar(self, response, nome):
        return self._aplicar(
            response, nome,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx',
        )


class MetadadosPDF(MetadadosDownload):
    def aplicar(self, response, nome):
        return self._aplicar(response, nome, 'application/pdf', 'pdf')
