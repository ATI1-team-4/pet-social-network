from django.shortcuts import render


def home(request):
    """Vista principal de bienvenida para verificar el funcionamiento del sistema."""
    return render(request, 'core/home.html')
