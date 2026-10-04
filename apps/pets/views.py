from django.shortcuts import render


def pet_management_view(request):
    """Renderiza la pantalla oficial de Gestión de Perfiles de Mascotas."""
    return render(request, 'pets/pet_management.html')


def pet_select_view(request):
    """Renderiza la pantalla oficial de Seleccionar Mascota activa."""
    return render(request, 'pets/pet_select.html')


def match_feed_view(request):
    """Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad)."""
    return render(request, 'pets/match_feed.html')


def match_interested_view(request):
    """Renderiza la pantalla oficial de Interesados - Mascotas Interesadas y citas."""
    return render(request, 'pets/match_interested.html')
