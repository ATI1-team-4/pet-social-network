"""
Configuración de rutas URL para el proyecto Petly.

La lista `urlpatterns` enruta las URLs hacia las vistas correspondientes.

Para más información, consulta:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/

Ejemplos:
Vistas basadas en funciones:
    1. Agregar importación: from my_app import views
    2. Agregar ruta a urlpatterns: path('', views.home, name='home')
Vistas basadas en clases:
    1. Agregar importación: from other_app.views import Home
    2. Agregar ruta a urlpatterns: path('', Home.as_view(), name='home')
Incluir otro archivo de URLs:
    1. Importar la función include(): from django.urls import include, path
    2. Agregar ruta a urlpatterns: path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
]

# Servir archivos multimedia durante el desarrollo local
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


