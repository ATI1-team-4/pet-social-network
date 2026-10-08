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


# Candidatos oficiales para el feed interactivo de cruza/compatibilidad (reto 11, página 13)
MATCH_CANDIDATES = [
    {
        'id': 'cand-bella',
        'name': 'Bella',
        'gender': 'hembra',
        'gender_label': 'Hembra',
        'gender_symbol': '♀',
        'species': 'perro',
        'species_label': 'Perro',
        'breed': 'Pastor Australiano (Perro) • Blue Merle Tricolor',
        'breed_short': 'Pastor Australiano',
        'age': '2.5 años',
        'birth_date': '12 / Oct / 2022',
        'weight': '21.4 kg',
        'certificate': '#FCI-MX-88421',
        'certificate_label': 'Certificado FCI',
        'has_pedigree': True,
        'compatibility': '98%',
        'compatibility_num': 98,
        'distance': 'A 3.2 km',
        'location': 'Los Teques',
        'purpose': 'Cruza y Socialización',
        'photo_url': '/static/images/pets/bella.png',
        'photo_clean_url': '/static/images/pets/bella_clean.png',
        'temperaments': ['Juguetona', 'Sociable', 'Cariñosa', 'Ágil'],
        'description': (
            'Bella es una perrita alegre, noble y muy inteligente. Adora correr al aire libre, '
            'resolver acertijos de olfato y convivir tranquilamente con niños y otros caninos.'
        ),
        'tutors': {
            'name': 'Sofía & Carlos',
            'location': 'Los Teques',
            'rating': '5.0',
            'review_count': '18 citas',
            'avatar_letter': 'SC',
        },
    },
    {
        'id': 'cand-kira',
        'name': 'Kira',
        'gender': 'hembra',
        'gender_label': 'Hembra',
        'gender_symbol': '♀',
        'species': 'perro',
        'species_label': 'Perro',
        'breed': 'Pomerania Mini',
        'breed_short': 'Pomerania Mini',
        'age': '2 años',
        'birth_date': '15 / Jun / 2023',
        'weight': '3.2 kg',
        'certificate': '#FCI-VE-11029',
        'certificate_label': 'Certificado FCI',
        'has_pedigree': True,
        'compatibility': '95%',
        'compatibility_num': 95,
        'distance': 'A 1.2 km',
        'location': 'Caracas',
        'purpose': 'Cruza responsable',
        'photo_url': '/static/images/pets/kira.png',
        'photo_clean_url': '/static/images/pets/kira.png',
        'temperaments': ['Tranquila', 'Cariñosa', 'Sociable'],
        'description': (
            'Kira es súper dócil, tierna y juguetona en calma. Buscamos una cruza ética '
            'certificada con contrato de seguimiento mutuo.'
        ),
        'tutors': {
            'name': 'Mariana Ríos',
            'location': 'Caracas',
            'rating': '4.9',
            'review_count': '12 citas',
            'avatar_letter': 'MR',
        },
    },
    {
        'id': 'cand-maya',
        'name': 'Maya',
        'gender': 'hembra',
        'gender_label': 'Hembra',
        'gender_symbol': '♀',
        'species': 'perro',
        'species_label': 'Perro',
        'breed': 'Boston Terrier',
        'breed_short': 'Boston Terrier',
        'age': '3.1 años',
        'birth_date': '08 / Ene / 2022',
        'weight': '7.8 kg',
        'certificate': '#FCI-VE-99412',
        'certificate_label': 'Certificado FCI',
        'has_pedigree': True,
        'compatibility': '92%',
        'compatibility_num': 92,
        'distance': 'A 4.5 km',
        'location': 'El Hatillo',
        'purpose': 'Socialización',
        'photo_url': '/static/images/pets/maya.png',
        'photo_clean_url': '/static/images/pets/maya.png',
        'temperaments': ['Curiosa', 'Juguetona', 'Protectora'],
        'description': (
            'Maya es activa, adora los paseos largos por el parque y jugar con pelotas. '
            'Muy cariñosa con la familia y otros compañeros caninos.'
        ),
        'tutors': {
            'name': 'Alejandro Gómez',
            'location': 'El Hatillo',
            'rating': '4.8',
            'review_count': '9 citas',
            'avatar_letter': 'AG',
        },
    },
]

# Pretendientes y citas confirmadas para la bandeja de interesados (reto 11, página 12)
INTERESTED_SUITORS = [
    {
        'id': 'suitor-kira',
        'name': 'Kira',
        'gender': 'hembra',
        'gender_symbol': '♀',
        'breed': 'Pomerania Mini',
        'age': '2 años',
        'birth_date': '15/06/2023',
        'certificate': 'Certificado FCI',
        'distance': 'A 1.2 km de ti',
        'location': 'Pomerania',
        'match_percentage': '98%',
        'is_recent': True,
        'recent_label': 'Match Reciente (Hace 2h)',
        'photo_url': '/static/images/pets/kira.png',
        'temperaments': ['Tranquila', 'Cariñosa'],
        'quote': (
            '¡Hola Sofía! Nos encantó Toby. Kira es súper dócil, tierna y juguetona en calma. '
            'Buscamos una cruza ética certificada para fin de año con contrato de seguimiento mutuo.'
        ),
        'tutor_signature': 'Mariana Ríos (Tutora de Kira)',
    },
    {
        'id': 'suitor-chloe',
        'name': 'Chloe',
        'gender': 'hembra',
        'gender_symbol': '♀',
        'breed': 'Bulldog Francés',
        'age': '1 año',
        'distance': 'A 2.1 km',
        'match_percentage': '91%',
        'badge_label': 'Solicitud previa',
        'photo_url': '/static/images/pets/chloe.png',
        'temperaments': ['Juguetona', 'Cariñosa'],
    },
    {
        'id': 'suitor-maya',
        'name': 'Maya',
        'gender': 'hembra',
        'gender_symbol': '♀',
        'breed': 'Boston Terrier',
        'age': '3.1 años',
        'distance': 'A 4.5 km',
        'match_percentage': '92%',
        'photo_url': '/static/images/pets/maya.png',
        'temperaments': ['Curiosa', 'Sociable'],
    },
]

CONFIRMED_DATES = [
    {
        'id': 'date-1',
        'badge': 'Confirmado por ambos',
        'day': 'Este Sábado',
        'title': 'Cita con Luna & Thor',
        'location': 'Parque España (Zona Canina Verificada)',
        'time': '11:00 AM',
    }
]


def match_feed_view(request):
    """
    Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad, reto 11 pág. 13).
    Aplica el color de perfil personalizado de la mascota activa al contenedor de descubrimiento,
    soporta alternar candidatos tipo tarjeta y desplegar el diálogo modal interactivo de match.
    """
    active_pet_id = request.session.get('active_pet_id', '1234')
    pet_param = request.GET.get('pet', '').strip().lower()

    if pet_param in ('luna', '5678') or (not pet_param and active_pet_id == '5678'):
        active_pet = DEFAULT_PETS[1]
        other_pet = DEFAULT_PETS[0]
    else:
        active_pet = DEFAULT_PETS[0]
        other_pet = DEFAULT_PETS[1]

    context = {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'candidates': MATCH_CANDIDATES,
        'current_candidate': MATCH_CANDIDATES[0],
        'candidates_json': json.dumps(MATCH_CANDIDATES),
        'interested_sidebar': INTERESTED_SUITORS,
        'interested_count': len(INTERESTED_SUITORS),
    }
    return render(request, 'pets/match_feed.html', context)


def match_interested_view(request):
    """
    Renderiza la pantalla oficial de Interesados - Mascotas Interesadas y citas (reto 11 pág. 12).
    Permite al tutor revisar pretendientes, concertar encuentros, enviar mensajes o volver al feed.
    """
    active_pet_id = request.session.get('active_pet_id', '1234')
    pet_param = request.GET.get('pet', '').strip().lower()

    if pet_param in ('luna', '5678') or (not pet_param and active_pet_id == '5678'):
        active_pet = DEFAULT_PETS[1]
        other_pet = DEFAULT_PETS[0]
    else:
        active_pet = DEFAULT_PETS[0]
        other_pet = DEFAULT_PETS[1]

    context = {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'suitors': INTERESTED_SUITORS,
        'featured_suitor': INTERESTED_SUITORS[0],
        'secondary_suitors': INTERESTED_SUITORS[1:],
        'interested_count': len(INTERESTED_SUITORS),
        'confirmed_dates': CONFIRMED_DATES,
    }
    return render(request, 'pets/match_interested.html', context)
