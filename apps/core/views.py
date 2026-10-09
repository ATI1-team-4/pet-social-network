from django.shortcuts import redirect, render


def home(request):
    """Vista principal de bienvenida para verificar el funcionamiento del sistema."""
    if request.user.is_authenticated:
        return redirect('pets:pet_select')
    return render(request, 'core/home.html')

