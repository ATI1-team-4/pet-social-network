"""
Configuración WSGI para el proyecto Petly.

Expone el invocable WSGI como una variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, consulta:
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
