"""
Configuración del proyecto SGR · Sistema de Gestión de Resultados
Ilustre Municipalidad de La Serena — Delegaciones Municipales

Proyecto Integrado INACAP. Etapa de templates: el proyecto funciona sin base
de datos. Los datos viven en memoria (core/datos.py) y la sesión se guarda en
una cookie firmada, de modo que basta con `python manage.py runserver`.
"""

import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Seguridad
# En producción la clave se entrega por variable de entorno y DEBUG se apaga.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'SGR_SECRET_KEY',
    'solo-desarrollo-cambiar-en-produccion-sgr-inacap-2026',
)
DEBUG = os.environ.get('SGR_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('SGR_HOSTS', 'localhost,127.0.0.1').split(',')

# ---------------------------------------------------------------------------
# Aplicaciones
# El admin de Django usa auth y contenttypes sobre SQLite (solo desarrollo).
# El SGR sigue usando sus cuentas en memoria (core/datos.py).
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sgr.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.sgr',
            ],
        },
    },
]

WSGI_APPLICATION = 'sgr.wsgi.application'

# ---------------------------------------------------------------------------
# Base de datos
# SQLite solo para el admin de Django. El modelo definitivo es sgr_schema.sql
# (MySQL 8) y se conectará en la etapa de desarrollo.
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sesión en cookie firmada: no necesita tabla de sesiones.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 8  # una jornada laboral

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ---------------------------------------------------------------------------
# Idioma y hora
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = False

# ---------------------------------------------------------------------------
# Archivos estáticos
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Parámetros del SGR
# La fecha de referencia fija el "día de hoy" del prototipo para que los
# cálculos sean reproducibles y coincidan con el script SQL: al 12-09-2026
# han transcurrido 74 de 91 días del trimestre, y lo esperado es 81,32 %.
# ---------------------------------------------------------------------------
SGR_FECHA_REFERENCIA = date(2026, 9, 12)
SGR_EVIDENCIA_FORMATOS = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}
SGR_EVIDENCIA_MAX_MB = 2
