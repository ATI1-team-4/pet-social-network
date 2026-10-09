import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

# Perfiles de mascotas de referencia según prototipo oficial (reto 11, páginas 10 y 11)
DEFAULT_PETS = [
    {
        'id': '1234',
        'name': 'Toby',
        'species': 'perro',
        'species_label': 'Perro',
        'gender': 'macho',
        'gender_label': 'Macho',
        'gender_symbol': '♂',
        'breed': 'Bulldog Francés',
        'birth_date': '04/15/2022',
        'birth_date_iso': '2022-04-15',
        'age_years': 3,
        'age_text': '3 años',
        'age_completed': '3 años cumplidos',
        'certificate': 'fci',
        'certificate_label': 'Certificado FCI / Con Pedigrí',
        'temperaments': ['Juguetón', 'Sociable', 'Cariñoso'],
        'description': 'Adora correr en el parque, jugar con pelotas y dormir siestas al sol. Muy amigable con otros perros.',
        'profile_color': 'coral',
        'profile_color_hex': '#FA7D82',
        'is_matching': True,
        'is_socializing': True,
        'is_adoption': False,
        'photo_url': '/static/images/pets/Toby.png',
        'is_active': True,
        'status_label': 'Activo',
        'tab_label': 'Toby',
    },
    {
        'id': '5678',
        'name': 'Luna',
        'species': 'perro',
        'species_label': 'Perro',
        'gender': 'hembra',
        'gender_label': 'Hembra',
        'gender_symbol': '♀',
        'breed': 'Golden Retriever',
        'birth_date': '06/20/2021',
        'birth_date_iso': '2021-06-20',
        'age_years': 4,
        'age_text': '4 años',
        'age_completed': '4 años cumplidos',
        'certificate': 'fci',
        'certificate_label': 'Pedigrí Certificado',
        'temperaments': ['Tranquilo', 'Cariñoso', 'Curioso'],
        'description': 'Le encanta nadar, buscar pelotas en el parque y descansar en familia.',
        'profile_color': 'lilac',
        'profile_color_hex': '#F5D0FF',
        'is_matching': True,
        'is_socializing': False,
        'is_adoption': False,
        'photo_url': '/static/images/pets/Luna.png',
        'is_active': False,
        'status_label': 'Inactiva',
        'tab_label': 'Luna (Golden Retriever)',
    },
]


def pet_management_view(request):
    """
    Renderiza la pantalla oficial de Gestión de Perfiles de Mascotas (reto 11, página 10).
    Permite alternar pestañas entre las mascotas del tutor, editar datos y marcas,
    o limpiar el formulario para registrar una nueva mascota.
    """
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        pet_name = request.POST.get('name', 'Mascota')
        if action == 'delete':
            messages.success(
                request,
                _('La mascota %(name)s ha sido eliminada exitosamente.') % {'name': pet_name},
            )
        else:
            messages.success(
                request, _('Los datos de %(name)s se guardaron exitosamente.') % {'name': pet_name}
            )
        return redirect('pets:pet_management')

    # Determinar mascota activa inicial por parámetro de consulta
    pet_param = request.GET.get('pet', '').strip().lower()
    is_new = request.GET.get('new', '').strip().lower() == 'true'

    active_pet = None
    if not is_new:
        if pet_param in ('luna', '5678'):
            active_pet = DEFAULT_PETS[1]
        else:
            active_pet = DEFAULT_PETS[0]

    context = {
        'pets': DEFAULT_PETS,
        'active_pet': active_pet,
        'is_new': is_new,
        'pets_json': json.dumps(DEFAULT_PETS),
    }
    return render(request, 'pets/pet_management.html', context)


def pet_select_view(request):
    """
    Renderiza la pantalla intermedia oficial de Selección de Mascota activa (reto 11, página 11)
    antes de avanzar hacia el flujo de emparejamiento (match feed).
    """
    if request.method == 'POST':
        selected_id = request.POST.get('selected_pet_id', '1234')
        request.session['active_pet_id'] = selected_id
        return redirect('pets:match_feed')

    selected_param = request.GET.get('selected', '').strip().lower()
    selected_id = '5678' if selected_param in ('luna', '5678') else '1234'

    # Copia de lista de mascotas marcando cuál está activa según selección
    pets_display = []
    active_pet_obj = None
    for pet in DEFAULT_PETS:
        pet_copy = dict(pet)
        pet_copy['is_selected'] = pet['id'] == selected_id
        if pet_copy['is_selected']:
            active_pet_obj = pet_copy
        pets_display.append(pet_copy)

    context = {
        'pets': pets_display,
        'active_pet': active_pet_obj or pets_display[0],
        'interested_count': 4,
    }
    return render(request, 'pets/pet_select.html', context)


def match_feed_view(request):
    """Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad)."""
    return render(request, 'pets/match_feed.html')


def match_interested_view(request):
    """Renderiza la pantalla oficial de Interesados - Mascotas Interesadas y citas."""
    return render(request, 'pets/match_interested.html')
