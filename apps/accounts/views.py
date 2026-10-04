from django.contrib.auth import logout
from django.shortcuts import redirect, render


def login_view(request):
    """Renderiza la pantalla oficial de Inicio de Sesión."""
    return render(request, 'accounts/login.html')


def register_view(request):
    """Renderiza la pantalla oficial de Registro de Usuario."""
    return render(request, 'accounts/register.html')


def password_reset_view(request):
    """Renderiza la pantalla oficial de Recuperación de Contraseña."""
    return render(request, 'accounts/password_reset.html')


def logout_view(request):
    """Cierra la sesión activa del usuario y redirige al inicio."""
    logout(request)
    return redirect('core:home')


def profile_view(request):
    """Renderiza la pantalla oficial de Gestión de Usuario (perfil del tutor)."""
    return render(request, 'accounts/user_profile.html')
