import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.pets.forms import ScheduleMeetupForm
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies
from apps.pets.services import (
    accept_match_request,
    calculate_candidate_distance,
    cancel_pet_meetup,
    get_all_match_requests_for_pet,
    get_interested_match_requests,
    get_match_candidates,
    get_requests_tab_counters,
    get_sent_match_requests,
    get_upcoming_pet_meetups,
    record_candidate_like,
    record_candidate_pass,
    reject_match_request,
    report_candidate_pet,
    schedule_pet_meetup,
    send_initial_match_note,
    serialize_candidate,
    serialize_match_request,
    serialize_pet_meetup,
)


def get_user_active_pet(request):
    """
    Obtiene la mascota activa del usuario autenticado basándose estrictamente en la sesión (cookie).
    Criterios de resolución:
    1. request.session['active_pet_id'] si aún pertenece a una mascota válida del usuario.
    2. Primera mascota del usuario registrada en base de datos por defecto.

    Retorna tupla: (active_pet, user_pets_list).
    Si el usuario no tiene mascotas registradas, limpia la sesión y retorna (None, []).
    """
    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if not user_pets:
        request.session.pop('active_pet_id', None)
        request.session.modified = True
        return None, []

    active_pet = None
    session_pet_id = str(request.session.get('active_pet_id', '')).strip().lower()
    if session_pet_id:
        active_pet = next(
            (p for p in user_pets if str(p.id) == session_pet_id or p.name.lower() == session_pet_id),
            None,
        )

    if not active_pet:
        active_pet = user_pets[0]

    request.session['active_pet_id'] = str(active_pet.id)
    request.session.modified = True
    return active_pet, user_pets


def get_default_new_pet_data():
    """Retorna la estructura inicial con valores por defecto para el formulario de registro de mascota."""
    return {
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
        'temperaments': [_('Juguetón')],
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


def serialize_pet_for_management(pet):
    """Serializa una mascota de la base de datos para la vista de gestión de perfiles."""
    return {
        'id': str(pet.id),
        'name': pet.name,
        'species': pet.species.slug if pet.species else 'perro',
        'species_label': str(pet.species_label),
        'gender': pet.gender,
        'gender_label': str(pet.gender_label),
        'gender_icon': pet.gender_icon,
        'breed': pet.breed,
        'birth_date': pet.birth_date.strftime('%m/%d/%Y') if pet.birth_date else '',
        'birth_date_iso': pet.birth_date.isoformat() if pet.birth_date else '',
        'age_years': pet.age_years,
        'age_text': str(pet.age_text),
        'age_completed': _('%(years)s años cumplidos') % {'years': pet.age_years},
        'certificate': pet.certificate,
        'certificate_label': str(pet.certificate_type or _('Certificado FCI / con pedigrí')),
        'temperaments': [t.strip() for t in pet.temperaments.split(',') if t.strip()]
        if pet.temperaments
        else [_('Juguetón')],
        'description': pet.description,
        'profile_color': pet.profile_color,
        'profile_color_hex': pet.profile_color_hex,
        'is_matching': pet.is_matching,
        'is_socializing': pet.is_socializing,
        'is_adoption': pet.is_adoption,
        'photo_url': pet.photo_url,
        'is_active': pet.is_matching,
        'status_label': _('Activo') if pet.is_matching else _('Inactiva'),
        'tab_label': pet.name,
    }


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
        db_pet.is_socializing = is_socializing
        if is_matching and is_socializing:
            db_pet.purpose = Pet.Purpose.BOTH
        elif is_matching and not is_socializing:
            db_pet.purpose = Pet.Purpose.MATING
        elif not is_matching and is_socializing:
            db_pet.purpose = Pet.Purpose.PLAY
        else:
            db_pet.purpose = Pet.Purpose.MATING
        db_pet.is_for_adoption = is_adoption

        raw_cert = request.POST.get('certificate', '').strip().lower()
        cert_map = {
            'fci': 'Certificado FCI',
            'tramite': 'En trámite',
            'sin_pedigri': 'Sin pedigrí',
        }
        cert_label = cert_map.get(raw_cert)
        if cert_label:
            db_pet.certificate_type = cert_label
            if raw_cert in ('sin_pedigri', 'tramite'):
                db_pet.certificate_number = ''

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
            is_socializing=is_socializing,
            purpose=purpose_val,
            is_for_adoption=is_adoption,
            certificate_type=cert_label,
        )
        if uploaded_photo:
            db_pet.photo = uploaded_photo
            db_pet.save()
        final_photo_url = db_pet.photo_url
        pet_id = str(db_pet.id)
        request.session['active_pet_id'] = pet_id
        request.session.modified = True

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
        'fci': _('Certificado FCI'),
        'tramite': _('En trámite'),
        'sin_pedigri': _('Sin pedigrí'),
    }
    cert_label = cert_map.get(certificate_val, _('Certificado FCI'))

    db_pet = None
    if str(pet_id).isdigit():
        db_pet = Pet.objects.filter(id=int(pet_id), owner=request.user).first()
    if not db_pet:
        db_pet = Pet.objects.filter(name__iexact=str(pet_id), owner=request.user).first()

    if not db_pet:
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada o no pertenece al usuario actual.')},
            status=404,
        )

    db_pet.certificate_type = cert_label
    if certificate_val in ('sin_pedigri', 'tramite'):
        db_pet.certificate_number = ''
    db_pet.save()

    return JsonResponse(
        {
            'status': 'success',
            'message': _('Certificado actualizado correctamente.'),
            'pet_id': db_pet.id,
            'certificate': certificate_val,
            'certificate_label': cert_label,
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
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada o no pertenece al usuario actual.')},
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
        db_pet.is_socializing = is_enabled
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
    Si el usuario no tiene mascotas, fuerza el modo de creación (is_new = True).
    """
    is_new = request.GET.get('new', '').strip().lower() == 'true'

    active_pet_obj, user_pets = get_user_active_pet(request)
    pets_list = [serialize_pet_for_management(p) for p in user_pets]

    if not user_pets:
        # El usuario no tiene mascotas registradas: forzar creación de primera mascota
        is_new = True
        active_pet = get_default_new_pet_data()
    elif is_new:
        active_pet = get_default_new_pet_data()
    else:
        active_pet = next(
            (p for p in pets_list if p['id'] == str(active_pet_obj.id)),
            pets_list[0] if pets_list else get_default_new_pet_data(),
        )

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

    if not pet:
        messages.error(
            request,
            _('La mascota especificada no existe o no tienes permisos para eliminarla.'),
        )
        return redirect('pets:pet_management')

    pet_name = pet.name
    was_active = str(request.session.get('active_pet_id', '')) == str(pet.id)
    pet.delete()

    # Si se eliminó la mascota activa en sesión, asignar otra mascota del usuario o limpiar
    if was_active:
        remaining_pet = Pet.objects.filter(owner=request.user).first()
        if remaining_pet:
            request.session['active_pet_id'] = str(remaining_pet.id)
        else:
            request.session.pop('active_pet_id', None)
        request.session.modified = True

    messages.success(
        request,
        _('La mascota %(name)s ha sido eliminada exitosamente.') % {'name': pet_name},
    )
    return redirect('pets:pet_management')


@login_required
@require_POST
def pet_set_active_view(request):
    """
    Establece la mascota activa seleccionada y la preferencia de pedigrí en la sesión
    del usuario (cookie) y redirige a la vista solicitada (o match feed), o retorna JSON si es AJAX.
    """
    selected_id = ''
    next_url = ''
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            selected_id = str(data.get('selected_pet_id', '')).strip()
            next_url = data.get('next', '') or data.get('next_url', '')
        except Exception:
            pass
    if not selected_id:
        selected_id = request.POST.get('selected_pet_id', '').strip()
    if not next_url:
        next_url = request.POST.get('next', '') or request.POST.get('next_url', '') or request.GET.get('next', '')

    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if not user_pets:
        messages.info(
            request,
            _('Para comenzar la búsqueda de pareja, primero debes registrar a tu mascota.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    active_pet = None
    if selected_id:
        target_str = selected_id.lower()
        active_pet = next(
            (p for p in user_pets if str(p.id) == target_str or p.name.lower() == target_str),
            None,
        )

    if not active_pet:
        active_pet = user_pets[0]

    resolved_id = str(active_pet.id)
    request.session['active_pet_id'] = resolved_id
    request.session.modified = True

    pedigree_filter = request.POST.get('pedigree_filter', 'both').strip().lower()
    if pedigree_filter not in ('with_pedigree', 'without_pedigree', 'both'):
        pedigree_filter = 'both'
    request.session['match_pedigree_preference'] = pedigree_filter

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
    )
    if is_ajax and not request.POST.get('is_form_submission'):
        return JsonResponse({'status': 'success', 'active_pet_id': resolved_id})

    if next_url and next_url.startswith('/'):
        return redirect(next_url)

    return redirect('pets:match_feed')


@login_required
def pet_select_view(request):
    """
    Renderiza la pantalla intermedia oficial de Selección de Mascota activa (reto 11, página 11)
    antes de avanzar hacia el flujo de emparejamiento (match feed).
    Carga las mascotas registradas por el usuario tutor autenticado y sincroniza
    la mascota elegida en la sesión. Si el usuario no tiene mascotas, redirige a registrar una.
    """
    active_pet_obj, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request,
            _('Para comenzar la búsqueda de pareja y explorar pretendientes, primero debes registrar a tu mascota.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    selected_id = str(active_pet_obj.id)

    pets_display = []
    for p in user_pets:
        has_fci = bool(p.has_pedigree and p.certificate == 'fci')
        p_interested_count = get_interested_match_requests(p).count()
        pets_display.append(
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
                'has_pedigree': p.has_pedigree,
                'certificate': 'fci' if has_fci else p.certificate,
                'certificate_label': str(p.certificate_type or ''),
                'profile_color': p.profile_color,
                'profile_color_hex': p.profile_color_hex,
                'interested_count': p_interested_count,
                'is_selected': str(p.id) == selected_id,
            }
        )

    active_pet_dict = next(
        (p for p in pets_display if p['id'] == selected_id),
        pets_display[0],
    )

    interested_count = active_pet_dict.get('interested_count', 0)

    pedigree_preference = request.session.get('match_pedigree_preference', 'both')
    if pedigree_preference not in ('with_pedigree', 'without_pedigree', 'both'):
        pedigree_preference = 'both'

    context = {
        'pets': pets_display,
        'active_pet': active_pet_dict,
        'interested_count': interested_count,
        'pedigree_preference': pedigree_preference,
    }
    return render(request, 'pets/pet_select.html', context)


@login_required
def match_feed_view(request):
    """
    Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad).
    Aplica el color de perfil personalizado de la mascota activa al contenedor de descubrimiento,
    soporta alternar candidatos dinámicos mediante el ORM y desplegar el diálogo modal interactivo de match.
    """
    active_pet, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request, _('Debes registrar al menos una mascota para acceder al feed de parejas.')
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    # Validar que la mascota activa tenga habilitada la condición de búsqueda de pareja (UC-08.3)
    if not active_pet.is_active_for_match:
        messages.warning(
            request,
            _('La mascota activa %(name)s no tiene habilitada la búsqueda de pareja.')
            % {'name': active_pet.name},
        )
        return redirect('pets:pet_select')

    other_pet = next((p for p in user_pets if p.id != active_pet.id), None)

    # Recarga manual del feed cuando no hay más candidatos o se desea reincorporar descartados
    if request.GET.get('reload') == 'true':
        MatchRequest.objects.filter(
            from_pet=active_pet,
            status=MatchRequest.RequestStatus.REJECTED,
        ).delete()
        request.session.pop('match_pedigree_preference', None)
        request.session.pop('match_max_distance', None)
        request.session.pop('match_purpose_preference', None)
        messages.info(request, _('El feed ha sido recargado con éxito.'))

    # Restablecimiento explícito de filtros
    if request.GET.get('reset_filters') == 'true':
        request.session.pop('match_pedigree_preference', None)
        request.session.pop('match_max_distance', None)
        request.session.pop('match_purpose_preference', None)
        messages.info(request, _('Los filtros han sido restablecidos.'))

    # Preferencia de pedigrí recibida vía GET o almacenada en la sesión
    pedigree_param = request.GET.get('pedigree') or request.session.get(
        'match_pedigree_preference', 'both'
    )
    if pedigree_param not in ('with_pedigree', 'without_pedigree', 'both'):
        pedigree_param = 'both'
    request.session['match_pedigree_preference'] = pedigree_param

    # Distancia máxima recibida vía GET o almacenada en la sesión
    raw_max_distance = request.GET.get('max_distance')
    if raw_max_distance is not None:
        try:
            max_distance = int(float(raw_max_distance))
            if max_distance < 1:
                max_distance = 1
            elif max_distance > 50:
                max_distance = 50
            request.session['match_max_distance'] = max_distance
        except (ValueError, TypeError):
            max_distance = request.session.get('match_max_distance', 5)
    else:
        max_distance = request.session.get('match_max_distance', 5)

    # Propósito de cruza/socialización recibido vía GET o almacenado en la sesión
    purpose_param = request.GET.get('purpose') or request.session.get(
        'match_purpose_preference', 'all'
    )
    if purpose_param not in ('all', 'mating', 'play', 'both'):
        purpose_param = 'all'
    request.session['match_purpose_preference'] = purpose_param

    match_filters = {'max_distance': max_distance}
    if pedigree_param == 'with_pedigree':
        match_filters['has_pedigree'] = True
    elif pedigree_param == 'without_pedigree':
        match_filters['without_pedigree'] = True
    if purpose_param != 'all':
        match_filters['purpose'] = purpose_param

    # Consultar candidatos compatibles mediante el ORM a través de services.py
    candidates_qs = get_match_candidates(active_pet, filters=match_filters)
    candidates_data = [serialize_candidate(active_pet, c) for c in candidates_qs]
    current_candidate = candidates_data[0] if candidates_data else None

    # Contadores sincronizados con la bandeja de solicitudes oficial (SRP)
    tab_counters = get_requests_tab_counters(active_pet)
    total_requests_count = tab_counters['all']
    interested_count = tab_counters['interested']
    pending_interested_count = tab_counters['pending']

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

    context = {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'candidates': candidates_data,
        'current_candidate': current_candidate,
        'candidates_json': json.dumps(candidates_data, cls=DjangoJSONEncoder),
        'interested_sidebar': interested_sidebar,
        'interested_count': interested_count,
        'pending_interested_count': pending_interested_count,
        'total_requests_count': total_requests_count,
        'tab_counters': tab_counters,
        'pedigree_preference': pedigree_param,
        'max_distance': max_distance,
        'purpose_preference': purpose_param,
    }
    return render(request, 'pets/match_feed.html', context)


@login_required
def match_interested_view(request):
    """
    Renderiza la pantalla oficial de Interesados - Solicitudes de emparejamiento y citas (UC-08.2).
    Permite al tutor revisar interesados (solicitudes recibidas), solicitudes enviadas,
    filtrar por pestañas y concertar encuentros seguros.
    Cumple con el Principio de Responsabilidad Única (SRP) delegando la lógica de consulta
    y conteo a apps/pets/services.py.
    """
    active_pet, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request,
            _('Debes registrar al menos una mascota antes de ver solicitudes e interesados.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    other_pet = next((p for p in user_pets if p.id != active_pet.id), None)

    # Contadores dinámicos por pestaña mediante services.py (SRP)
    tab_counters = get_requests_tab_counters(active_pet)

    # Filtrado por pestaña ('all', 'interested', 'sent', 'matches')
    tab = request.GET.get('tab', 'all').strip().lower()
    if tab == 'interested':
        requests_qs = get_interested_match_requests(active_pet)
    elif tab == 'sent':
        requests_qs = get_sent_match_requests(active_pet)
    elif tab == 'matches':
        requests_qs = (
            MatchRequest.objects.filter(
                Q(to_pet=active_pet) | Q(from_pet=active_pet),
                status=MatchRequest.RequestStatus.ACCEPTED,
            )
            .exclude(from_pet__owner=F('to_pet__owner'))
            .select_related(
                'from_pet',
                'to_pet',
                'from_pet__owner',
                'to_pet__owner',
                'from_pet__owner__profile',
                'to_pet__owner__profile',
            )
            .order_by('-created_at')
        )
    else:
        tab = 'all'
        requests_qs = get_all_match_requests_for_pet(active_pet)

    suitors = [serialize_match_request(active_pet, r) for r in requests_qs] if active_pet else []

    # Criterio de ordenamiento ('compatibility', 'distance', 'recent')
    sort_by = request.GET.get('sort', 'compatibility').strip().lower()
    if sort_by not in ['compatibility', 'distance', 'recent']:
        sort_by = 'compatibility'

    if suitors:
        if sort_by == 'compatibility':
            suitors.sort(
                key=lambda s: (s.get('compatibility_val', 0), s.get('created_timestamp', 0)),
                reverse=True,
            )
        elif sort_by == 'distance':
            suitors.sort(
                key=lambda s: (s.get('distance_val', 999.0), -s.get('created_timestamp', 0))
            )
        elif sort_by == 'recent':
            suitors.sort(key=lambda s: s.get('created_timestamp', 0), reverse=True)

    # Citas confirmadas o próximas desde PetMeetup
    meetups_qs = get_upcoming_pet_meetups(active_pet) if active_pet else []
    confirmed_dates = [serialize_pet_meetup(active_pet, m) for m in meetups_qs]

    context = {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'suitors': suitors,
        'requests': suitors,
        'featured_suitor': suitors[0] if suitors else None,
        'secondary_suitors': suitors[1:] if len(suitors) > 1 else [],
        'interested_count': tab_counters.get('interested', 0),
        'tab_counters': tab_counters,
        'current_tab': tab,
        'current_sort': sort_by,
        'confirmed_dates': confirmed_dates,
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
    Acepta una solicitud de match recibida en la bandeja de interesados.
    Valida pertenencia a la mascota activa del usuario y delega a services.accept_match_request.
    """
    active_pet = None
    active_pet_id = request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = Pet.objects.filter(id=int(active_pet_id), owner=request.user).first()
    if not active_pet:
        active_pet = Pet.objects.filter(owner=request.user).first()

    if not active_pet:
        return JsonResponse(
            {'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')},
            status=400,
        )

    try:
        match_request = accept_match_request(request_id=request_id, active_pet=active_pet)
        tab_counters = get_requests_tab_counters(active_pet)
        return JsonResponse(
            {
                'status': 'success',
                'match_status': 'accepted',
                'request_id': match_request.id,
                'message': _('Solicitud de match aceptada exitosamente.'),
                'tab_counters': tab_counters,
            }
        )
    except MatchRequest.DoesNotExist:
        return JsonResponse(
            {
                'status': 'error',
                'message': _(
                    'La solicitud de match no existe o no corresponde a tu mascota activa.'
                ),
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=400,
        )


@login_required
@require_POST
def match_reject_request_view(request, request_id):
    """
    Descarta o rechaza una solicitud de match en la bandeja de interesados.
    Valida pertenencia a la mascota activa del usuario y delega a services.reject_match_request.
    """
    active_pet = None
    active_pet_id = request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = Pet.objects.filter(id=int(active_pet_id), owner=request.user).first()
    if not active_pet:
        active_pet = Pet.objects.filter(owner=request.user).first()

    if not active_pet:
        return JsonResponse(
            {'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')},
            status=400,
        )

    try:
        match_request = reject_match_request(request_id=request_id, active_pet=active_pet)
        tab_counters = get_requests_tab_counters(active_pet)
        return JsonResponse(
            {
                'status': 'success',
                'match_status': 'rejected',
                'request_id': match_request.id,
                'message': _('Solicitud descartada exitosamente.'),
                'tab_counters': tab_counters,
            }
        )
    except MatchRequest.DoesNotExist:
        return JsonResponse(
            {
                'status': 'error',
                'message': _(
                    'La solicitud de match no existe o no corresponde a tu mascota activa.'
                ),
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=400,
        )


@login_required
@require_POST
def send_initial_note_view(request, request_id):
    """
    Registra o actualiza la nota inicial de contacto tras un match aceptado
    o durante la interacción con una solicitud de match.
    Persiste en MatchRequest.notes mediante services.send_initial_match_note.
    """
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    if not data:
        data = request.POST

    note_text = (
        data.get('note')
        or data.get('notes')
        or data.get('note_text')
        or data.get('message')
        or data.get('initial_message', '')
    )
    note_text = str(note_text).strip()

    if not note_text:
        return JsonResponse(
            {'status': 'error', 'message': _('La nota no puede estar vacía.')},
            status=400,
        )

    try:
        result = send_initial_match_note(
            request_id=request_id,
            sender_user=request.user,
            note_text=note_text,
        )
        return JsonResponse(result)
    except MatchRequest.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': _('La solicitud de match no fue encontrada.')},
            status=404,
        )
    except PermissionError as pe:
        return JsonResponse(
            {'status': 'error', 'message': str(pe)},
            status=403,
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=400,
        )


# ==============================================================================
# Siluetas de Controladores: Citas y Encuentros Caninos (Issue #65)
# ==============================================================================


@login_required
@require_POST
def schedule_meetup_view(request):
    """
    Procesa la concertación de un encuentro canino seguro desde el modal.
    - Valida los datos recibidos mediante ScheduleMeetupForm(data).
    - Identifica la mascota solicitante y la mascota destinataria.
    - Delega la creación y persistencia a apps.pets.services.schedule_pet_meetup(...).
    - Retorna JSON con confirmación y serialización del encuentro.
    """
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    if not data:
        data = request.POST.copy()

    form = ScheduleMeetupForm(data)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse(
            {
                'status': 'error',
                'message': str(first_error),
                'errors': form.errors,
            },
            status=400,
        )

    # Identificar mascota solicitante del usuario
    requester_pet_id = (
        data.get('requester_pet_id')
        or data.get('from_pet_id')
        or request.session.get('active_pet_id')
    )
    requester_pet = None
    if requester_pet_id:
        requester_pet = Pet.objects.filter(id=requester_pet_id, owner=request.user).first()
    if not requester_pet:
        requester_pet = Pet.objects.filter(owner=request.user).first()

    if not requester_pet:
        return JsonResponse(
            {
                'status': 'error',
                'message': _('Debes tener al menos una mascota registrada para agendar citas.'),
            },
            status=400,
        )

    # Identificar mascota destinataria
    target_pet_id = data.get('target_pet_id') or data.get('to_pet_id') or data.get('pet_id')
    match_request_id = data.get('match_request_id') or data.get('request_id')
    target_pet = None

    if match_request_id:
        req = MatchRequest.objects.filter(id=match_request_id).first()
        if req:
            target_pet = req.to_pet if req.from_pet_id == requester_pet.id else req.from_pet

    if not target_pet and target_pet_id:
        target_pet = Pet.objects.filter(id=target_pet_id).first()

    if not target_pet:
        target_pet_name = str(data.get('target_pet_name') or data.get('pet_name') or '').strip()
        if target_pet_name:
            target_pet = (
                Pet.objects.filter(name__iexact=target_pet_name)
                .exclude(id=requester_pet.id)
                .first()
            )

    if not target_pet:
        return JsonResponse(
            {
                'status': 'error',
                'message': _('Debe especificar una mascota destinataria válida para el encuentro.'),
            },
            status=400,
        )

    try:
        meetup = schedule_pet_meetup(
            requester_user=request.user,
            requester_pet=requester_pet,
            target_pet=target_pet,
            meeting_date=form.cleaned_data['date'],
            meeting_time=form.cleaned_data['time'],
            location_name=form.cleaned_data['location_name'],
            notes=form.cleaned_data.get('notes', ''),
        )
        return JsonResponse(
            {
                'status': 'scheduled',
                'message': _('¡Cita agendada con éxito! Se ha notificado al tutor de la mascota.'),
                'meetup_id': meetup.id,
                'meetup': serialize_pet_meetup(requester_pet, meetup),
            }
        )
    except PermissionError as pe:
        return JsonResponse({'status': 'error', 'message': str(pe)}, status=403)
    except ValueError as ve:
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def cancel_meetup_view(request, meetup_id):
    """
    Cancela una cita de encuentro canino previamente acordada.
    - Valida permisos del usuario sobre el encuentro.
    - Delega la actualización a apps.pets.services.cancel_pet_meetup(meetup_id, request.user).
    - Retorna JSON con confirmación de cancelación.
    """
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    if not data:
        data = request.POST

    reason = str(data.get('reason', '')).strip()

    try:
        meetup = cancel_pet_meetup(meetup_id=meetup_id, user=request.user, reason=reason)
        return JsonResponse(
            {
                'status': 'cancelled',
                'message': _('La cita ha sido cancelada exitosamente.'),
                'meetup_id': meetup.id,
            }
        )
    except PetMeetup.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': _('La cita especificada no existe.')},
            status=404,
        )
    except PermissionError as pe:
        return JsonResponse({'status': 'error', 'message': str(pe)}, status=403)
    except ValueError as ve:
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
