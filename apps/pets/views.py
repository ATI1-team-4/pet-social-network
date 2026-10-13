import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.pets.models import MatchRequest, Pet, PetSpecies
from apps.pets.services import (
    calculate_candidate_distance,
    get_match_candidates,
    record_candidate_like,
    record_candidate_pass,
    report_candidate_pet,
    serialize_candidate,
)

# Perfiles de mascotas de referencia según prototipo oficial (reto 11, páginas 10 y 11)
DEFAULT_PETS = [
    {
        'id': '1234',
        'name': 'Toby',
        'species': 'perro',
        'species_label': 'Perro',
        'gender': 'M',
        'gender_label': 'Macho',
        'gender_icon': 'male',
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
        'gender': 'H',
        'gender_label': 'Hembra',
        'gender_icon': 'female',
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
        'profile_color_hex': '#8A4AF3',
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
        'lilac': '#8A4AF3',
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

        # Objetivos en PetMatch
        is_matching = request.POST.get('is_matching') in ('true', 'on', '1', True)
        is_socializing = request.POST.get('is_socializing') in ('true', 'on', '1', True)
        is_adoption = request.POST.get('is_adoption') in ('true', 'on', '1', True)

        db_pet.is_active_for_match = is_matching
        if is_matching and is_socializing:
            db_pet.purpose = Pet.Purpose.BOTH
        elif is_matching and not is_socializing:
            db_pet.purpose = Pet.Purpose.MATING
        elif not is_matching and is_socializing:
            db_pet.purpose = Pet.Purpose.PLAY
        else:
            db_pet.purpose = Pet.Purpose.MATING
        db_pet.is_for_adoption = is_adoption

        # Certificado / pedigrí
        raw_cert = request.POST.get('certificate', '').strip().lower()
        cert_map = {
            'fci': 'Certificado FCI',
            'tramite': 'En trámite',
            'sin_pedigri': 'Sin pedigrí',
        }
        cert_label = cert_map.get(raw_cert)
        if cert_label:
            db_pet.certificate_type = cert_label

        if remove_photo and db_pet.photo:
            db_pet.photo.delete(save=False)
            db_pet.photo = None

        if uploaded_photo:
            db_pet.photo = uploaded_photo

        db_pet.save()
        final_photo_url = db_pet.photo_url
        pet_id = str(db_pet.id)
    else:
        # Crear nueva mascota oficial en BD para el tutor autenticado
        species_obj, _sp_created = PetSpecies.objects.get_or_create(
            slug=species_slug,
            defaults={'name': species_slug.capitalize(), 'icon_name': 'dog'},
        )
        is_matching = request.POST.get('is_matching') in ('true', 'on', '1', True)
        is_socializing = request.POST.get('is_socializing') in ('true', 'on', '1', True)
        is_adoption = request.POST.get('is_adoption') in ('true', 'on', '1', True)

        purpose_val = Pet.Purpose.BOTH
        if is_matching and not is_socializing:
            purpose_val = Pet.Purpose.MATING
        elif not is_matching and is_socializing:
            purpose_val = Pet.Purpose.PLAY

        raw_cert = request.POST.get('certificate', '').strip().lower()
        cert_map = {
            'fci': 'Certificado FCI',
            'tramite': 'En trámite',
            'sin_pedigri': 'Sin pedigrí',
        }
        cert_label = cert_map.get(raw_cert, 'Certificado FCI')

        db_pet = Pet.objects.create(
            owner=request.user,
            name=pet_name,
            species=species_obj,
            breed=request.POST.get('breed', 'Mestizo'),
            gender=gender,
            birth_date=birth_date_val,
            profile_color=profile_color,
            description=request.POST.get('description', ''),
            temperaments=request.POST.get('temperaments', ''),
            is_active_for_match=is_matching,
            purpose=purpose_val,
            is_for_adoption=is_adoption,
            certificate_type=cert_label,
        )
        if uploaded_photo:
            db_pet.photo = uploaded_photo
            db_pet.save()
        final_photo_url = db_pet.photo_url
        pet_id = str(db_pet.id)

    # Actualizar la mascota en DEFAULT_PETS en memoria para consistencia
    for pet in DEFAULT_PETS:
        if pet['id'] == pet_id or (not pet_id and pet['name'] == pet_name):
            pet['name'] = pet_name
            pet['breed'] = request.POST.get('breed', pet['breed'])
            pet['species'] = species_slug
            pet['species_label'] = (
                _('Gato')
                if species_slug == 'gato'
                else (_('Otro') if species_slug == 'otro' else _('Perro'))
            )
            pet['gender'] = 'H' if gender == Pet.Gender.HEMBRA else 'M'
            pet['gender_icon'] = 'female' if gender == Pet.Gender.HEMBRA else 'male'
            pet['gender_label'] = _('Hembra') if gender == Pet.Gender.HEMBRA else _('Macho')
            pet['birth_date'] = request.POST.get('birth_date', pet.get('birth_date', '04/15/2022'))
            pet['description'] = request.POST.get('description', pet.get('description', ''))
            pet['profile_color'] = profile_color
            pet['profile_color_hex'] = color_hex
            pet['is_matching'] = is_matching
            pet['is_socializing'] = is_socializing
            pet['is_adoption'] = is_adoption
            pet['is_active'] = is_matching
            if raw_cert and raw_cert in cert_map:
                pet['certificate'] = raw_cert
                pet['certificate_label'] = cert_map[raw_cert]
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
@require_POST
def pet_update_certificate_view(request):
    """
    Actualiza de forma asíncrona (AJAX / fetch) el tipo de certificado / pedigrí de una mascota.
    """
    try:
        data = (
            json.loads(request.body) if request.content_type == 'application/json' else request.POST
        )
    except Exception:
        data = request.POST

    pet_id = data.get('pet_id')
    certificate_val = data.get('certificate', '').strip().lower()

    if not pet_id or not certificate_val:
        return JsonResponse(
            {'status': 'error', 'message': _('Parámetros incompletos.')},
            status=400,
        )

    cert_map = {
        'fci': 'Certificado FCI',
        'tramite': 'En trámite',
        'sin_pedigri': 'Sin pedigrí',
    }
    cert_label = cert_map.get(certificate_val, 'Certificado FCI')

    db_pet = None
    if str(pet_id).isdigit():
        db_pet = Pet.objects.filter(id=int(pet_id), owner=request.user).first()
    if not db_pet:
        db_pet = Pet.objects.filter(name__iexact=str(pet_id), owner=request.user).first()

    if not db_pet:
        # Fallback a DEFAULT_PETS en memoria si no está en BD
        for p in DEFAULT_PETS:
            if p['id'] == str(pet_id) or p['name'].lower() == str(pet_id).lower():
                p['certificate'] = certificate_val
                p['certificate_label'] = cert_label
                return JsonResponse(
                    {
                        'status': 'success',
                        'message': _('Certificado actualizado correctamente.'),
                        'pet_id': p['id'],
                        'certificate': certificate_val,
                        'certificate_label': cert_label,
                    }
                )
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada.')},
            status=404,
        )

    db_pet.certificate_type = cert_label
    db_pet.save()

    return JsonResponse(
        {
            'status': 'success',
            'message': _('Certificado actualizado correctamente.'),
            'pet_id': db_pet.id,
            'certificate': db_pet.certificate,
            'certificate_label': db_pet.certificate_type,
        }
    )


@login_required
@require_POST
def pet_toggle_goal_view(request):
    """
    Actualiza de forma asíncrona (AJAX / fetch) uno de los objetivos en PetMatch
    (is_matching, is_socializing o is_adoption) para la mascota del tutor.
    """
    try:
        data = (
            json.loads(request.body) if request.content_type == 'application/json' else request.POST
        )
    except Exception:
        data = request.POST

    pet_id = data.get('pet_id')
    goal = data.get('goal')
    value = data.get('value')

    if not pet_id or not goal:
        return JsonResponse(
            {'status': 'error', 'message': _('Parámetros incompletos.')},
            status=400,
        )

    db_pet = None
    if str(pet_id).isdigit():
        db_pet = Pet.objects.filter(id=int(pet_id), owner=request.user).first()
    if not db_pet:
        db_pet = Pet.objects.filter(name__iexact=str(pet_id), owner=request.user).first()

    if not db_pet:
        # Fallback a DEFAULT_PETS en memoria si no está en BD
        for p in DEFAULT_PETS:
            if p['id'] == str(pet_id) or p['name'].lower() == str(pet_id).lower():
                is_enabled = value in (True, 'true', 'on', '1', 1)
                p[goal] = is_enabled
                if goal == 'is_matching':
                    p['is_active'] = is_enabled
                    p['status_label'] = _('Activo') if is_enabled else _('Inactiva')
                return JsonResponse(
                    {
                        'status': 'success',
                        'message': _('Objetivo actualizado correctamente.'),
                        'pet_id': p['id'],
                        'goal': goal,
                        'value': is_enabled,
                    }
                )

        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada.')},
            status=404,
        )

    is_enabled = value in (True, 'true', 'on', '1', 1)

    if goal == 'is_matching':
        db_pet.is_active_for_match = is_enabled
        if is_enabled:
            db_pet.purpose = Pet.Purpose.BOTH if db_pet.is_socializing else Pet.Purpose.MATING
        else:
            db_pet.purpose = Pet.Purpose.PLAY if db_pet.is_socializing else Pet.Purpose.MATING

    elif goal == 'is_socializing':
        if is_enabled:
            db_pet.purpose = Pet.Purpose.BOTH if db_pet.is_matching else Pet.Purpose.PLAY
        else:
            db_pet.purpose = Pet.Purpose.MATING

    elif goal == 'is_adoption':
        db_pet.is_for_adoption = is_enabled

    else:
        return JsonResponse(
            {'status': 'error', 'message': _('Objetivo no válido.')},
            status=400,
        )

    db_pet.save()

    return JsonResponse(
        {
            'status': 'success',
            'message': _('Objetivo actualizado correctamente.'),
            'pet_id': db_pet.id,
            'goal': goal,
            'value': is_enabled,
            'is_matching': db_pet.is_matching,
            'is_socializing': db_pet.is_socializing,
            'is_adoption': db_pet.is_adoption,
        }
    )


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
            pets_list.append(
                {
                    'id': str(p.id),
                    'name': p.name,
                    'species': p.species.slug if p.species else 'perro',
                    'species_label': str(p.species_label),
                    'gender': p.gender,
                    'gender_label': str(p.gender_label),
                    'gender_icon': p.gender_icon,
                    'breed': p.breed,
                    'birth_date': p.birth_date.strftime('%m/%d/%Y')
                    if p.birth_date
                    else '04/15/2022',
                    'birth_date_iso': p.birth_date.isoformat() if p.birth_date else '2022-04-15',
                    'age_years': p.age_years,
                    'age_text': str(p.age_text),
                    'age_completed': f'{p.age_years} años cumplidos',
                    'certificate': p.certificate,
                    'certificate_label': str(p.certificate_type or 'Certificado FCI / con pedigrí'),
                    'temperaments': [t.strip() for t in p.temperaments.split(',') if t.strip()]
                    if p.temperaments
                    else ['Juguetón'],
                    'description': p.description,
                    'profile_color': p.profile_color,
                    'profile_color_hex': p.profile_color_hex,
                    'is_matching': p.is_matching,
                    'is_socializing': p.is_socializing,
                    'is_adoption': p.is_adoption,
                    'photo_url': p.photo_url,
                    'is_active': p.is_matching,
                    'status_label': 'Activo' if p.is_matching else 'Inactiva',
                    'tab_label': p.name,
                }
            )
    else:
        pets_list = DEFAULT_PETS

    active_pet = None
    if is_new:
        active_pet = {
            'id': '',
            'name': '',
            'species': 'perro',
            'species_label': _('Perro'),
            'gender': 'M',
            'gender_label': _('Macho'),
            'gender_icon': 'male',
            'breed': '',
            'birth_date': '',
            'birth_date_iso': '',
            'age_years': 0,
            'age_text': _('0 años'),
            'certificate': 'fci',
            'certificate_label': _('Certificado FCI'),
            'temperaments': ['Juguetón'],
            'description': '',
            'profile_color': 'coral',
            'profile_color_hex': '#FA7D82',
            'is_matching': True,
            'is_socializing': True,
            'is_adoption': False,
            'photo_url': '',
            'is_active': True,
            'status_label': _('Activo'),
            'tab_label': _('Nueva mascota'),
        }
    elif pets_list:
        if pet_param:
            active_pet = next(
                (p for p in pets_list if p['name'].lower() == pet_param or p['id'] == pet_param),
                pets_list[0],
            )
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
    selected_id = request.POST.get('selected_pet_id', '').strip()
    if not selected_id:
        user_first = Pet.objects.filter(owner=request.user).first()
        selected_id = str(user_first.id) if user_first else '1234'
    request.session['active_pet_id'] = selected_id
    return redirect('pets:match_feed')


@login_required
def pet_select_view(request):
    """
    Renderiza la pantalla intermedia oficial de Selección de Mascota activa (reto 11, página 11)
    antes de avanzar hacia el flujo de emparejamiento (match feed).
    Carga las mascotas registradas por el usuario tutor autenticado y sincroniza
    la mascota elegida en la sesión.
    """
    selected_param = request.GET.get('selected', '').strip().lower()
    session_pet_id = str(request.session.get('active_pet_id', '')).strip().lower()

    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if user_pets:
        pets_source = []
        for p in user_pets:
            has_fci = bool(
                'fci' in (p.certificate_type or '').lower()
                or (p.certificate_number and 'fci' in p.certificate_number.lower())
                or p.has_pedigree
            )
            pets_source.append(
                {
                    'id': str(p.id),
                    'name': p.name,
                    'species': p.species.slug if p.species else 'perro',
                    'species_label': str(p.species_label),
                    'gender': p.gender,
                    'gender_label': str(p.gender_label),
                    'gender_icon': p.gender_icon,
                    'is_hembra': p.is_hembra,
                    'breed': p.breed,
                    'age_text': str(p.age_text),
                    'photo_url': p.photo_url,
                    'is_active': p.is_active_for_match,
                    'is_matching': p.is_active_for_match,
                    'certificate': 'fci' if has_fci else '',
                    'certificate_label': str(p.certificate_type or ''),
                    'profile_color': p.profile_color,
                    'profile_color_hex': p.profile_color_hex,
                }
            )
    else:
        # Fallback de compatibilidad con datos de demostración
        pets_source = [dict(pet) for pet in DEFAULT_PETS]

    # Determinar la mascota activa (prioridad: parámetro GET > sesión activa > primera mascota)
    active_pet_obj = None
    if selected_param:
        active_pet_obj = next(
            (
                p
                for p in pets_source
                if str(p['id']).lower() == selected_param or p['name'].lower() == selected_param
            ),
            None,
        )
    if not active_pet_obj and session_pet_id:
        active_pet_obj = next(
            (
                p
                for p in pets_source
                if str(p['id']).lower() == session_pet_id or p['name'].lower() == session_pet_id
            ),
            None,
        )
    if not active_pet_obj and pets_source:
        active_pet_obj = pets_source[0]

    selected_id = str(active_pet_obj['id']) if active_pet_obj else ''

    # Marcar 'is_selected' para cada tarjeta
    pets_display = []
    for pet in pets_source:
        pet_copy = dict(pet)
        pet_copy['is_selected'] = str(pet['id']) == selected_id
        pets_display.append(pet_copy)

    # Sincronizar en la sesión
    if selected_id:
        request.session['active_pet_id'] = selected_id

    # Contabilizar solicitudes de match pendientes entrantes hacia la mascota activa
    interested_count = 0
    if active_pet_obj and str(active_pet_obj.get('id', '')).isdigit():
        interested_count = MatchRequest.objects.filter(
            to_pet_id=int(active_pet_obj['id']),
            status=MatchRequest.RequestStatus.PENDING,
        ).count()
    elif active_pet_obj:
        interested_count = 4

    context = {
        'pets': pets_display,
        'active_pet': active_pet_obj or (pets_display[0] if pets_display else None),
        'interested_count': interested_count,
    }
    return render(request, 'pets/pet_select.html', context)


# Pretendientes y citas confirmadas para la bandeja de interesados (reto 11, página 12)
INTERESTED_SUITORS = [
    {
        'id': 'suitor-kira',
        'name': 'Kira',
        'gender': 'hembra',
        'gender_icon': 'female',
        'breed': 'Pomerania Mini',
        'age': '2 años',
        'birth_date': '15/06/2023',
        'certificate': 'Certificado FCI',
        'distance': 'A 1.2 km de ti',
        'distance_val': 1.2,
        'location': 'Pomerania',
        'match_percentage': '98%',
        'compatibility_val': 98,
        'category': 'breeding',
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
        'gender_icon': 'female',
        'breed': 'Bulldog Francés',
        'age': '1 año',
        'birth_date': '20/09/2024',
        'certificate': 'Certificado Veterinario',
        'distance': 'A 2.1 km',
        'distance_val': 2.1,
        'location': 'Bulldog Francés',
        'match_percentage': '91%',
        'compatibility_val': 91,
        'category': 'breeding',
        'is_recent': True,
        'recent_label': 'Match reciente (hace 5h)',
        'badge_label': 'Solicitud previa',
        'photo_url': '/static/images/pets/default_avatar.svg',
        'temperaments': ['Juguetona', 'Cariñosa'],
        'quote': (
            '¡Hola! Nos encanta la energía de Toby. Chloe es súper alegre, tierna y juguetona. '
            'Buscamos socialización activa o cruza responsable con chequeos de salud previos.'
        ),
        'tutor_signature': 'Carlos Gómez (Tutor de Chloe)',
    },
    {
        'id': 'suitor-maya',
        'name': 'Maya',
        'gender': 'hembra',
        'gender_icon': 'female',
        'breed': 'Boston Terrier',
        'age': '3.1 años',
        'birth_date': '10/02/2022',
        'certificate': 'Pedigrí Oficial',
        'distance': 'A 4.5 km',
        'distance_val': 4.5,
        'location': 'Boston Terrier',
        'match_percentage': '92%',
        'compatibility_val': 92,
        'category': 'social',
        'is_recent': False,
        'recent_label': 'Match ayer',
        'photo_url': '/static/images/pets/default_avatar.svg',
        'temperaments': ['Curiosa', 'Sociable'],
        'quote': (
            '¡Hola! Maya está lista para nuevas amistades caninas y paseos grupales los fines de semana. '
            'Cuenta con todas sus vacunas al día y excelente temperamento con otros perritos.'
        ),
        'tutor_signature': 'Elena Torres (Tutora de Maya)',
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
    Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad).
    Aplica el color de perfil personalizado de la mascota activa al contenedor de descubrimiento,
    soporta alternar candidatos dinámicos mediante el ORM y desplegar el diálogo modal interactivo de match.
    """
    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if not user_pets:
        # Fallback a mascotas activas globales si el usuario aún no tiene mascotas registradas
        user_pets = list(Pet.objects.filter(is_active_for_match=True).order_by('id'))

    if not user_pets:
        messages.warning(
            request, _('Debes registrar al menos una mascota para acceder al feed de parejas.')
        )
        return redirect('pets:pet_select')

    active_pet = None
    active_pet_id = request.session.get('active_pet_id')
    pet_param = request.GET.get('pet', '').strip().lower()

    if pet_param:
        if pet_param.isdigit():
            active_pet = next((p for p in user_pets if str(p.id) == pet_param), None)
        if not active_pet:
            active_pet = next((p for p in user_pets if p.name.lower() == pet_param), None)

    if not active_pet and active_pet_id:
        active_pet = next((p for p in user_pets if str(p.id) == str(active_pet_id)), None)
        if not active_pet and str(active_pet_id) == '5678':
            active_pet = next((p for p in user_pets if p.name.lower() == 'luna'), None)
        elif not active_pet and str(active_pet_id) == '1234':
            active_pet = next((p for p in user_pets if p.name.lower() == 'toby'), None)

    if not active_pet:
        active_pet = user_pets[0]

    # Validar que la mascota activa tenga habilitada la condición de búsqueda de pareja (UC-08.3)
    if not active_pet.is_active_for_match:
        messages.warning(
            request,
            _('La mascota activa %(name)s no tiene habilitada la búsqueda de pareja.')
            % {'name': active_pet.name},
        )
        return redirect('pets:pet_select')

    if 'active_pet_id' not in request.session:
        request.session['active_pet_id'] = str(active_pet.id)
    other_pet = next((p for p in user_pets if p.id != active_pet.id), None)

    # Consultar candidatos compatibles mediante el ORM a través de services.py
    candidates_qs = get_match_candidates(active_pet)
    candidates_data = [serialize_candidate(active_pet, c) for c in candidates_qs]
    current_candidate = candidates_data[0] if candidates_data else None

    # Consultar solicitudes de match entrantes para la barra lateral de interesados
    interested_requests = (
        MatchRequest.objects.filter(
            to_pet=active_pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        .select_related('from_pet', 'from_pet__owner', 'from_pet__owner__profile')
        .order_by('-created_at')
    )
    interested_sidebar = []
    for req in interested_requests[:5]:
        cand = req.from_pet
        interested_sidebar.append(
            {
                'id': str(req.id),
                'candidate_pet_id': cand.id,
                'name': cand.name,
                'age': str(cand.age_text),
                'breed': cand.breed,
                'distance': calculate_candidate_distance(active_pet, cand),
                'photo_url': cand.photo_url,
            }
        )
    interested_count = interested_requests.count()

    context = {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'candidates': candidates_data,
        'current_candidate': current_candidate,
        'candidates_json': json.dumps(candidates_data, cls=DjangoJSONEncoder),
        'interested_sidebar': interested_sidebar,
        'interested_count': interested_count,
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


# ==============================================================================
# Controladores Atómicos: Feed y Swipe de Candidatos (Issue #63)
# ==============================================================================


@login_required
@require_POST
def match_like_candidate_view(request):
    """
    Registra 'Me gusta' hacia un candidato del feed y verifica coincidencia recíproca.
    """
    try:
        data = (
            json.loads(request.body) if request.content_type == 'application/json' else request.POST
        )
    except Exception:
        data = request.POST

    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return JsonResponse(
            {'status': 'error', 'message': _('ID de candidato no especificado.')},
            status=400,
        )

    try:
        candidate_pet = Pet.objects.get(id=candidate_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse(
            {'status': 'error', 'message': _('Candidato no encontrado.')},
            status=404,
        )

    # Identificar mascota activa del usuario autenticado
    active_pet = None
    active_pet_id = data.get('active_pet_id') or request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = Pet.objects.filter(id=int(active_pet_id), owner=request.user).first()
    if not active_pet:
        active_pet = Pet.objects.filter(owner=request.user).first()

    if not active_pet:
        return JsonResponse(
            {'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')},
            status=400,
        )

    if not active_pet.is_active_for_match:
        return JsonResponse(
            {
                'status': 'error',
                'message': _('La mascota activa no tiene habilitada la búsqueda de pareja.'),
            },
            status=400,
        )

    if candidate_pet.id == active_pet.id or candidate_pet.owner_id == request.user.id:
        return JsonResponse(
            {'status': 'error', 'message': _('No puedes interactuar con tu propia mascota.')},
            status=400,
        )

    match_request, is_mutual = record_candidate_like(active_pet, candidate_pet)

    return JsonResponse(
        {
            'status': 'success',
            'is_match': is_mutual,
            'match_request_id': match_request.id,
            'active_pet': {
                'id': active_pet.id,
                'name': active_pet.name,
                'photo_url': active_pet.photo_url,
            },
            'candidate': {
                'id': candidate_pet.id,
                'name': candidate_pet.name,
                'photo_url': candidate_pet.photo_url,
                'tutor_name': candidate_pet.owner.get_full_name() or candidate_pet.owner.username,
            },
        }
    )


@login_required
@require_POST
def match_pass_candidate_view(request):
    """
    Registra el descarte de un candidato en el feed para avanzar a la siguiente tarjeta.
    """
    try:
        data = (
            json.loads(request.body) if request.content_type == 'application/json' else request.POST
        )
    except Exception:
        data = request.POST

    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return JsonResponse(
            {'status': 'error', 'message': _('ID de candidato no especificado.')},
            status=400,
        )

    try:
        candidate_pet = Pet.objects.get(id=candidate_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse(
            {'status': 'error', 'message': _('Candidato no encontrado.')},
            status=404,
        )

    active_pet = None
    active_pet_id = data.get('active_pet_id') or request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = Pet.objects.filter(id=int(active_pet_id), owner=request.user).first()
    if not active_pet:
        active_pet = Pet.objects.filter(owner=request.user).first()

    if not active_pet:
        return JsonResponse(
            {'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')},
            status=400,
        )

    match_request = record_candidate_pass(active_pet, candidate_pet)

    return JsonResponse(
        {
            'status': 'success',
            'candidate_id': candidate_pet.id,
            'match_request_id': match_request.id,
        }
    )


@login_required
@require_POST
def match_report_candidate_view(request):
    """
    Registra una denuncia o reporte contra una mascota candidata desde el feed.
    """
    try:
        data = (
            json.loads(request.body) if request.content_type == 'application/json' else request.POST
        )
    except Exception:
        data = request.POST

    reported_pet_id = data.get('candidate_id') or data.get('reported_pet_id')
    reason = data.get('reason', '').strip()

    if not reported_pet_id:
        return JsonResponse(
            {'status': 'error', 'message': _('ID de mascota candidata no especificado.')},
            status=400,
        )

    try:
        reported_pet = Pet.objects.get(id=reported_pet_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota candidata no encontrada.')},
            status=404,
        )

    report = report_candidate_pet(
        reporter_user=request.user,
        reported_pet=reported_pet,
        reason=reason,
    )

    # Registrar descarte automático para que no vuelva a aparecer en el feed
    active_pet = None
    active_pet_id = request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = Pet.objects.filter(id=int(active_pet_id), owner=request.user).first()
    if not active_pet:
        active_pet = Pet.objects.filter(owner=request.user).first()

    if active_pet:
        record_candidate_pass(active_pet, reported_pet)

    return JsonResponse(
        {
            'status': 'success',
            'report_id': report.id,
            'message': _(
                'El reporte ha sido enviado al equipo de administración para su revisión.'
            ),
        }
    )


# ==============================================================================
# Siluetas de Controladores: Solicitudes e Interesados (Issue #64)
# ==============================================================================


@login_required
@require_POST
def match_accept_request_view(request, request_id):
    """
    Silueta: Acepta una solicitud de match recibida en la bandeja de interesados.

    El equipo debe implementar:
    - Validar que la solicitud pertenezca a la mascota activa del usuario.
    - Delegar la actualización a `apps.pets.services.accept_match_request(request_id, active_pet)`.
    - Retornar JSON con `{'status': 'accepted', 'request_id': request_id}`.
    """
    return JsonResponse(
        {
            'status': 'pending_implementation',
            'message': _('Pendiente de implementación por el equipo.'),
        },
        status=501,
    )


@login_required
@require_POST
def match_reject_request_view(request, request_id):
    """
    Silueta: Descarta o rechaza una solicitud de match en la bandeja de interesados.

    El equipo debe implementar:
    - Validar que la solicitud pertenezca a la mascota activa del usuario.
    - Delegar la actualización a `apps.pets.services.reject_match_request(request_id, active_pet)`.
    - Retornar JSON con `{'status': 'rejected', 'request_id': request_id}`.
    """
    return JsonResponse(
        {
            'status': 'pending_implementation',
            'message': _('Pendiente de implementación por el equipo.'),
        },
        status=501,
    )


@login_required
@require_POST
def send_initial_note_view(request, request_id):
    """
    Silueta: Envía o actualiza la nota de contacto asociada a la solicitud de match.

    El equipo debe implementar:
    - Obtener `note_text` (o `message_text`) desde el POST y validar contenido no vacío.
    - Delegar a `apps.pets.services.send_initial_match_note(...)`.
    - Retornar JSON con confirmación de registro de nota.
    """
    return JsonResponse(
        {
            'status': 'pending_implementation',
            'message': _('Pendiente de implementación por el equipo.'),
        },
        status=501,
    )


# ==============================================================================
# Siluetas de Controladores: Citas y Encuentros Caninos (Issue #65)
# ==============================================================================


@login_required
@require_POST
def schedule_meetup_view(request):
    """
    Silueta: Procesa la concertación de un encuentro canino seguro desde el modal.

    El equipo debe implementar:
    - Validar los datos recibidos mediante `ScheduleMeetupForm(request.POST)`.
    - Delegar la creación a `apps.pets.services.schedule_pet_meetup(...)`.
    - Retornar JSON con `{'status': 'scheduled', 'meetup_id': ...}`.
    """
    return JsonResponse(
        {
            'status': 'pending_implementation',
            'message': _('Pendiente de implementación por el equipo.'),
        },
        status=501,
    )


@login_required
@require_POST
def cancel_meetup_view(request, meetup_id):
    """
    Silueta: Cancela una cita de encuentro canino previamente acordada.

    El equipo debe implementar:
    - Validar permisos del usuario sobre el encuentro.
    - Delegar a `apps.pets.services.cancel_pet_meetup(meetup_id, request.user)`.
    - Retornar JSON con confirmación de cancelación.
    """
    return JsonResponse(
        {
            'status': 'pending_implementation',
            'message': _('Pendiente de implementación por el equipo.'),
        },
        status=501,
    )
