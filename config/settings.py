"""
Configuración de Django para el proyecto Petly.

Generado por 'django-admin startproject' usando Django 6.1.1.

Para más información sobre este archivo, consulta:
https://docs.djangoproject.com/en/6.1/topics/settings/

Para la lista completa de configuraciones y sus valores, consulta:
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Construir rutas dentro del proyecto de esta forma: BASE_DIR / 'subdirectorio'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno de desarrollo desde .env.dev (o .env)
load_dotenv(BASE_DIR / '.env.dev')
load_dotenv(BASE_DIR / '.env')



# Configuraciones iniciales de desarrollo - no aptas para producción
# Consulta https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# Clave secreta leída de variable de entorno con respaldo para desarrollo
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-development-key-petly-2026',
)

# Modo depuración controlado por variable de entorno (True por defecto en desarrollo)
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Hosts permitidos (dominios válidos a los que responde la aplicación)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

# Orígenes confiables para validación CSRF (peticiones POST seguras)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:8000,http://127.0.0.1:8000',
    ).split(',')
    if origin.strip()
]

# Identificación del dominio propio para enlaces absolutos (correos, recuperación de clave)
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')
SITE_PROTOCOL = os.environ.get('SITE_PROTOCOL', 'http')
SITE_URL = f"{SITE_PROTOCOL}://{SITE_DOMAIN}"



DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'tailwind',
    'theme',
]

LOCAL_APPS = [
    'apps.core',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Configuración de Tailwind CSS (django-tailwind)
TAILWIND_APP_NAME = 'theme'

INTERNAL_IPS = [
    '127.0.0.1',
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

# Recarga automática en el navegador exclusiva para desarrollo (Live Reload)
# No se carga ni afecta el entorno de producción (DEBUG=False)
if DEBUG:
    INSTALLED_APPS.append('django_browser_reload')
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Base de datos SQLite almacenada en la carpeta data/
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATA_DIR = BASE_DIR / os.environ.get('DATABASE_DIR', 'data')
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / os.environ.get('DATABASE_NAME', 'db.sqlite3'),
    }
}



# Validación de contraseñas
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internacionalización básica
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Caracas'

USE_I18N = True

USE_TZ = True


# Archivos estáticos (CSS, JavaScript, imágenes)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Archivos multimedia cargados por usuarios (fotos, videos, avatares)
# https://docs.djangoproject.com/en/6.1/topics/files/

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'



# Correo electrónico
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


# Configuración de registro de eventos (logging) hacia la consola del contenedor
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

