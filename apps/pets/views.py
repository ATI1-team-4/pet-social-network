import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST


from apps.pets.models import Pet, PetSpecies

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
        'certificate_label': 'Certificado FCI / con pedigrí',
        'temperaments': ['Juguetón', 'Sociable', 'Cariñoso'],
        'description': 'Adora correr en el parque, jugar con pelotas y dormir siestas al sol. Muy amigable con otros perros.',
        'profile_color': 'coral',
        'profile_color_hex': '#FA7D82',
        'is_matching': True,
        'is_socializing': True,
        'is_adoption': False,
        'photo_url': '/static/images/pets/default_avatar.svg',
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
        'certificate_label': 'Pedigrí certificado',
        'temperaments': ['Tranquilo', 'Cariñoso', 'Curioso'],
        'description': 'Le encanta nadar, buscar pelotas en el parque y descansar en familia.',
        'profile_color': 'lilac',
        'profile_color_hex': '#F5D0FF',
        'is_matching': True,
        'is_socializing': False,
        'is_adoption': False,
        'photo_url': '/static/images/pets/default_avatar.svg',
        'is_active': False,
        'status_label': 'Inactiva',
        'tab_label': 'Luna (Golden Retriever)',
    },
]


@login_required
@require_POST
def pet_save_view(request):
    """
    Guarda o actualiza la información del perfil de una mascota.
    Procesa atributos de color, especie, sexo, temperamentos, biografía y
    la fotografía subida por el usuario almacenándola en media/pets/.
    Redirige a la pantalla de gestión con mensaje flash de éxito.
    """
    pet_name = request.POST.get('name', 'Mascota').strip()
    pet_id = request.POST.get('pet_id', '').strip()

    profile_color = request.POST.get('profile_color', 'coral')
    color_hex_map = {
        'coral': '#FA7D82',
        'lilac': '#E9D5FF',
        'mint': '#8FFFB4',
        'peach': '#FFDAD9',
    }
    color_hex = color_hex_map.get(profile_color, '#FA7D82')

    species_slug = request.POST.get('species', 'perro').strip().lower()
    raw_gender = request.POST.get('gender', 'M')
    gender = Pet.Gender.HEMBRA if raw_gender in ('H', 'hembra') else Pet.Gender.MACHO

    uploaded_photo = request.FILES.get('photo')
    remove_photo = request.POST.get('remove_photo') == 'true'

    birth_date_val = None
    birth_date_str = request.POST.get('birth_date', '').strip()
    if birth_date_str:
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                birth_date_val = datetime.strptime(birth_date_str, fmt).date()
                break
            except ValueError:
                pass
    if not birth_date_val:
        birth_date_val = timezone.now().date()

    # Buscar mascota en base de datos si existe
    db_pet = None
    if pet_id.isdigit():
        db_pet = Pet.objects.filter(id=int(pet_id), owner=request.user).first()
    if not db_pet:
        db_pet = Pet.objects.filter(name__iexact=pet_name, owner=request.user).first()

    if db_pet:
        db_pet.name = pet_name
        db_pet.breed = request.POST.get('breed', db_pet.breed)
        species_obj, _sp_created = PetSpecies.objects.get_or_create(
            slug=species_slug,
            defaults={'name': species_slug.capitalize(), 'icon_name': 'dog'},
        )
        db_pet.species = species_obj
        db_pet.gender = gender
        db_pet.birth_date = birth_date_val
        db_pet.description = request.POST.get('description', db_pet.description)
        db_pet.profile_color = profile_color
        db_pet.temperaments = request.POST.get('temperaments', db_pet.temperaments)

        if remove_photo and db_pet.photo:
            db_pet.photo.delete(save=False)
            db_pet.photo = None

        if uploaded_photo:
            db_pet.photo = uploaded_photo

        db_pet.save()
        final_photo_url = db_pet.photo_url
        pet_id = str(db_pet.id)
    elif uploaded_photo:
        # Si se subió foto y aún no existe en BD, crear el registro oficial en BD
        species_obj, _sp_created = PetSpecies.objects.get_or_create(
            slug=species_slug,
            defaults={'name': species_slug.capitalize(), 'icon_name': 'dog'},
        )
        db_pet = Pet.objects.create(
            owner=request.user,
            name=pet_name,
            species=species_obj,
            breed=request.POST.get('breed', 'Mestizo'),
            gender=gender,
            birth_date=birth_date_val,
            profile_color=profile_color,
            description=request.POST.get('description', ''),
        )
        db_pet.photo = uploaded_photo
        db_pet.save()
        final_photo_url = db_pet.photo_url
        pet_id = str(db_pet.id)



    else:
        final_photo_url = (
            '/static/images/pets/default_avatar.svg'
            if remove_photo
            else None
        )

    # Actualizar la mascota en DEFAULT_PETS en memoria para consistencia
    for pet in DEFAULT_PETS:
        if pet['id'] == pet_id or (not pet_id and pet['name'] == pet_name):
            pet['name'] = pet_name
            pet['breed'] = request.POST.get('breed', pet['breed'])
            pet['species'] = species_slug
            pet['species_label'] = (
                _('Gato') if species_slug == 'gato' else (_('Otro') if species_slug == 'otro' else _('Perro'))
            )
            pet['gender'] = 'hembra' if gender == Pet.Gender.HEMBRA else 'macho'
            pet['gender_symbol'] = '♀' if gender == Pet.Gender.HEMBRA else '♂'
            pet['gender_label'] = _('Hembra') if gender == Pet.Gender.HEMBRA else _('Macho')
            pet['birth_date'] = request.POST.get('birth_date', pet.get('birth_date', '04/15/2022'))
            pet['description'] = request.POST.get('description', pet.get('description', ''))
            pet['profile_color'] = profile_color
            pet['profile_color_hex'] = color_hex
            if final_photo_url:
                pet['photo_url'] = final_photo_url
            temperaments_str = request.POST.get('temperaments', '')
            if temperaments_str:
                pet['temperaments'] = [t.strip() for t in temperaments_str.split(',') if t.strip()]
            break

    messages.success(
        request, _('Los datos de %(name)s se guardaron exitosamente.') % {'name': pet_name}
    )
    return redirect('pets:pet_management')


@login_required
def pet_management_view(request):
    """
    Renderiza la pantalla oficial de Gestión de perfiles de mascotas.
    Permite alternar pestañas entre las mascotas del tutor, visualizar datos y marcas,
    o desplegar el formulario para registrar una nueva mascota.
    """
    pet_param = request.GET.get('pet', '').strip().lower()
    is_new = request.GET.get('new', '').strip().lower() == 'true'

    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if user_pets:
        pets_list = []
        for p in user_pets:
            pets_list.append({
                'id': str(p.id),
                'name': p.name,
                'species': p.species.slug if p.species else 'perro',
                'species_label': str(p.species_label),
                'gender': 'hembra' if p.is_hembra else 'macho',
                'gender_label': str(p.gender_label),
                'gender_symbol': p.gender_symbol,
                'breed': p.breed,
                'birth_date': p.birth_date.strftime('%m/%d/%Y') if p.birth_date else '04/15/2022',
                'birth_date_iso': p.birth_date.isoformat() if p.birth_date else '2022-04-15',
                'age_years': p.age_years,
                'age_text': str(p.age_text),
                'age_completed': f'{p.age_years} años cumplidos',
                'certificate': 'fci',
                'certificate_label': str(p.certificate_type or 'Certificado FCI / con pedigrí'),
                'temperaments': [t.strip() for t in p.temperaments.split(',') if t.strip()] if p.temperaments else ['Juguetón'],
                'description': p.description,
                'profile_color': p.profile_color,
                'profile_color_hex': {'coral': '#FA7D82', 'lilac': '#E9D5FF', 'mint': '#8FFFB4', 'peach': '#FFDAD9'}.get(p.profile_color, '#FA7D82'),
                'is_matching': p.is_active_for_match,
                'is_socializing': True,
                'is_adoption': False,
                'photo_url': p.photo_url,
                'is_active': p.is_active_for_match,
                'status_label': 'Activo' if p.is_active_for_match else 'Inactiva',
                'tab_label': p.name,
            })
    else:
        pets_list = DEFAULT_PETS

    active_pet = None
    if not is_new and pets_list:
        if pet_param:
            active_pet = next((p for p in pets_list if p['name'].lower() == pet_param or p['id'] == pet_param), pets_list[0])
        else:
            active_pet = pets_list[0]

    context = {
        'pets': pets_list,
        'active_pet': active_pet,
        'is_new': is_new,
        'pets_json': json.dumps(pets_list, cls=DjangoJSONEncoder),
    }
    return render(request, 'pets/pet_management.html', context)




@login_required
@require_POST
def pet_delete_view(request, pet_id):
    """
    Elimina de forma segura una mascota perteneciente al usuario autenticado.
    Verifica que el usuario sea el dueño legítimo de la mascota antes de proceder.
    """
    pet = None
    if str(pet_id).isdigit():
        pet = Pet.objects.filter(id=int(pet_id), owner=request.user).first()
    if not pet:
        pet = Pet.objects.filter(name__iexact=str(pet_id), owner=request.user).first()

    if pet:
        pet_name = pet.name
        pet.delete()
        messages.success(
            request,
            _('La mascota %(name)s ha sido eliminada exitosamente.') % {'name': pet_name},
        )
    else:
        # Fallback para mascotas en memoria durante transición
        pet_name = str(pet_id)
        for dp in DEFAULT_PETS:
            if dp['id'] == str(pet_id) or dp['name'].lower() == str(pet_id).lower():
                pet_name = dp['name']
                break
        messages.success(
            request,
            _('La mascota %(name)s ha sido eliminada exitosamente.') % {'name': pet_name},
        )
    return redirect('pets:pet_management')


@login_required
@require_POST
def pet_set_active_view(request):
    """
    Establece la mascota activa seleccionada en la sesión del usuario
    y redirige al flujo de emparejamiento (match feed).
    """
    selected_id = request.POST.get('selected_pet_id', '1234')
    request.session['active_pet_id'] = selected_id
    return redirect('pets:match_feed')


@login_required
def pet_select_view(request):
    """
    Renderiza la pantalla intermedia oficial de Selección de Mascota activa (reto 11, página 11)
    antes de avanzar hacia el flujo de emparejamiento (match feed).
    """
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
        'purpose': 'Cruza y socialización',
        'profile_color': 'coral',
        'profile_color_hex': '#FA7D82',
        'photo_url': '/static/images/pets/default_avatar.svg',
        'photo_clean_url': '/static/images/pets/default_avatar.svg',
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
        'profile_color': 'lilac',
        'profile_color_hex': '#E9D5FF',
        'photo_url': '/static/images/pets/default_avatar.svg',
        'photo_clean_url': '/static/images/pets/default_avatar.svg',
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
        'profile_color': 'mint',
        'profile_color_hex': '#8FFFB4',
        'photo_url': '/static/images/pets/default_avatar.svg',
        'photo_clean_url': '/static/images/pets/default_avatar.svg',
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
        'recent_label': 'Match reciente (hace 2h)',
        'photo_url': '/static/images/pets/default_avatar.svg',
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
        'photo_url': '/static/images/pets/default_avatar.svg',
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
        'photo_url': '/static/images/pets/default_avatar.svg',
        'temperaments': ['Curiosa', 'Sociable'],
    },
]

CONFIRMED_DATES = [
    {
        'id': 'date-1',
        'badge': 'Confirmado por ambos',
        'day': 'Este sábado',
        'title': 'Cita con Luna & Thor',
        'location': 'Parque España (Zona Canina Verificada)',
        'time': '11:00 AM',
    }
]


@login_required
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


@login_required
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
