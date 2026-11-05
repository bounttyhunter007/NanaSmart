"""Banco descartável para testes, sem acessar o PostgreSQL de desenvolvimento."""

import os

from .settings import *  # noqa: F401,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
if os.environ.get('NANASMART_TEST_POSTGRES_PORT'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': '127.0.0.1',
        'PORT': os.environ['NANASMART_TEST_POSTGRES_PORT'],
        'TEST': {'NAME': 'test_nanasmart_alertas'},
    }}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
