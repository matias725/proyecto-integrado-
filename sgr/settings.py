"""
Configuración del SGR · Sistema de Gestión de Resultados
Ilustre Municipalidad de La Serena — Delegaciones Municipales

Toda la configuración sensible se lee de variables de entorno (archivo .env
en desarrollo, variables del servidor en AWS). Ver .env.example.
"""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env(nombre, defecto=None):
    return os.environ.get(nombre, defecto)


def env_bool(nombre, defecto=False):
    return env(nombre, '1' if defecto else '0').strip().lower() in ('1', 'true', 'si', 'sí', 'yes')


def env_lista(nombre, defecto=''):
    return [v.strip() for v in env(nombre, defecto).split(',') if v.strip()]


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
DEBUG = env_bool('SGR_DEBUG', False)
SECRET_KEY = env('SGR_SECRET_KEY') or ('solo-desarrollo-no-usar-en-produccion' if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError('Defina SGR_SECRET_KEY en el entorno (ver .env.example).')

ALLOWED_HOSTS = env_lista('SGR_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_lista('SGR_CSRF_ORIGENES')

# Detrás de un balanceador o Nginx que termina HTTPS
SGR_HTTPS = env_bool('SGR_HTTPS', False)
if SGR_HTTPS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('SGR_REDIRIGIR_HTTPS', True)
    SECURE_REDIRECT_EXEMPT = [r'^salud/$']          # el balanceador consulta por HTTP
    SECURE_HSTS_SECONDS = int(env('SGR_HSTS_SEGUNDOS', '3600'))

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 8          # una jornada laboral
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_FAILURE_VIEW = 'core.vistas_sistema.csrf_fallido'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'cuentas',
    'catalogos',
    'atenciones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cuentas.middleware.ContextoDelegacionMiddleware',
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
# SQLite para desarrollo y pruebas; MySQL 8 en AWS (SGR_DB_MOTOR=mysql).
# ---------------------------------------------------------------------------
if env('SGR_DB_MOTOR', 'sqlite') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('SGR_DB_NOMBRE', 'sgr_laserena'),
            'USER': env('SGR_DB_USUARIO', 'sgr'),
            'PASSWORD': env('SGR_DB_CLAVE', ''),
            'HOST': env('SGR_DB_HOST', '127.0.0.1'),
            'PORT': env('SGR_DB_PUERTO', '3306'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / env('SGR_DB_NOMBRE', 'db.sqlite3'),
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'cuentas.Usuario'
AUTHENTICATION_BACKENDS = ['cuentas.backends.UsuarioOCorreoBackend']
LOGIN_URL = 'acceso'
LOGIN_REDIRECT_URL = 'inicio'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
     'OPTIONS': {'user_attributes': ('nombre_usuario', 'nombre', 'correo')}},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'cuentas.validadores.ComplejidadClaveValidator'},
]

# ---------------------------------------------------------------------------
# Recuperación de contraseña (valores referenciales del diseño, configurables)
# ---------------------------------------------------------------------------
SGR_CODIGO_VIGENCIA_MIN = int(env('SGR_CODIGO_VIGENCIA_MIN', '10'))
SGR_CODIGO_REENVIO_SEG = int(env('SGR_CODIGO_REENVIO_SEG', '45'))
SGR_CODIGO_MAX_INTENTOS = int(env('SGR_CODIGO_MAX_INTENTOS', '5'))
SGR_CODIGO_MAX_POR_HORA = int(env('SGR_CODIGO_MAX_POR_HORA', '5'))
SGR_LOGIN_MAX_INTENTOS = int(env('SGR_LOGIN_MAX_INTENTOS', '5'))
SGR_LOGIN_BLOQUEO_MIN = int(env('SGR_LOGIN_BLOQUEO_MIN', '10'))

# ---------------------------------------------------------------------------
# Correo
# Por defecto los correos quedan en la bandeja de pruebas del sistema
# (visible para el superadministrador). En AWS puede usarse SMTP (SES, Gmail).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env('SGR_CORREO_BACKEND', 'cuentas.correo.BandejaBackend')
EMAIL_HOST = env('SGR_SMTP_HOST', '')
EMAIL_PORT = int(env('SGR_SMTP_PUERTO', '587'))
EMAIL_HOST_USER = env('SGR_SMTP_USUARIO', '')
EMAIL_HOST_PASSWORD = env('SGR_SMTP_CLAVE', '')
EMAIL_USE_TLS = env_bool('SGR_SMTP_TLS', True)
DEFAULT_FROM_EMAIL = env('SGR_CORREO_REMITENTE', 'SGR La Serena <no-responder@sgr.example.test>')
SGR_BANDEJA_REENVIAR_SMTP = env_bool('SGR_BANDEJA_REENVIAR_SMTP', False)

# ---------------------------------------------------------------------------
# Idioma y hora
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos (servidos por WhiteNoise)
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': ('django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
                    else 'whitenoise.storage.CompressedManifestStaticFilesStorage'),
    },
}

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ---------------------------------------------------------------------------
# Registro de eventos en la salida estándar (visible en CloudWatch o journalctl)
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'simple': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'}},
    'handlers': {'consola': {'class': 'logging.StreamHandler', 'formatter': 'simple'}},
    'root': {'handlers': ['consola'], 'level': env('SGR_LOG_NIVEL', 'INFO')},
}

# ---------------------------------------------------------------------------
# Parámetros del SGR
# ---------------------------------------------------------------------------
SGR_POR_PAGINA = 10
# Muestra las cuentas de evaluación en la pantalla de acceso (apagar en producción real)
SGR_CUENTAS_DEMO = env_bool('SGR_CUENTAS_DEMO', DEBUG)
SGR_VERSION = env('SGR_VERSION', 'ev2-1.0.0')

# Fecha fija para los módulos simulados heredados de la EV1, de modo que sus
# cálculos coincidan con el script SQL (74 de 91 días, 81,32 % esperado).
SGR_FECHA_REFERENCIA = date(2026, 9, 12)
SGR_EVIDENCIA_FORMATOS = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}
SGR_EVIDENCIA_MAX_MB = 2
