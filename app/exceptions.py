"""Erros de acesso ao banco continuam JSON nos endpoints da API."""
import logging

from django.db import InterfaceError, OperationalError, ProgrammingError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    if isinstance(exc, (InterfaceError, OperationalError, ProgrammingError)):
        logger.error('Falha de acesso ao banco na API.', exc_info=(type(exc), exc, exc.__traceback__))
        set_rollback()
        return Response({
            'detail': 'Não foi possível acessar o banco de dados. Verifique a conexão, a configuração e as migrações do backend.'
        }, status=503)
    return None
