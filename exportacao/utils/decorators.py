"""Decorator de objetos: registra o resultado sem alterar o arquivo gerado."""

import logging

from .base_exporter import Exportador


logger = logging.getLogger(__name__)


class ExportadorDecorator(Exportador):
    def __init__(self, exportador: Exportador):
        self._exportador = exportador

    def exportar(self, nome, titulo, colunas, linhas):
        return self._exportador.exportar(nome, titulo, colunas, linhas)


class ExportadorComLog(ExportadorDecorator):
    def exportar(self, nome, titulo, colunas, linhas):
        response = super().exportar(nome, titulo, colunas, linhas)
        # Não registra valores das células, usuários, tokens ou dados da empresa.
        logger.info(
            'Exportação concluída: gerador=%s bytes=%d',
            type(self._exportador).__name__, len(response.content),
        )
        return response
