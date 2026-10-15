import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.pets.forms import ScheduleMeetupForm
from apps.pets.models import MatchRequest, Pet, PetMeetup
from apps.pets.services import (
    accept_match_request,
    cancel_pet_meetup,
    delete_user_pet,
    get_default_new_pet_data,
    get_match_feed_context,
    get_match_interested_context,
    get_pet_select_context,
    get_requests_tab_counters,
    record_candidate_like,
    record_candidate_pass,
    reject_match_request,
    report_candidate_pet,
    save_or_update_pet,
    schedule_pet_meetup,
    send_initial_match_note,
    serialize_pet_for_management,
    serialize_pet_meetup,
    toggle_pet_goal,
    update_pet_certificate,
)


def parse_request_payload(request) -> dict:
    """Extrae uniformemente los datos enviados por JSON o formulario POST."""
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    return request.POST


def get_user_active_pet(request):
    """
    Obtiene la mascota activa del usuario autenticado basándose estrictamente en la cookie de sesión.
    Criterios de resolución:
    - Mascota indicada en request.session['active_pet_id'] si aún pertenece a una mascota válida del usuario.
    - Primera mascota del usuario registrada en base de datos por defecto.

    Retorna tupla: (active_pet, user_pets_list).
    Si el usuario no tiene mascotas registradas, limpia la sesión y retorna (None, []).
    """
    # Consultar mascotas registradas del usuario autenticado
    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if not user_pets:
        request.session.pop('active_pet_id', None)
        request.session.modified = True
        return None, []

    # Buscar la mascota activa correspondiente al ID guardado en la cookie de sesión
    active_pet = None
    session_pet_id = str(request.session.get('active_pet_id', '')).strip().lower()
    if session_pet_id:
        active_pet = next(
            (p for p in user_pets if str(p.id) == session_pet_id or p.name.lower() == session_pet_id),
            None,
        )

    # Si no hay mascota activa en sesión, asignar la primera del tutor
    if not active_pet:
        active_pet = user_pets[0]

    # Sincronizar el identificador de la mascota activa en la sesión del usuario
    request.session['active_pet_id'] = str(active_pet.id)
    request.session.modified = True
    return active_pet, user_pets


# ==============================================================================
# Vistas de Perfil y Gestión de Mascotas
# ==============================================================================


@login_required
def pet_management_view(request):
    """
    Renderiza la pantalla oficial de Gestión de perfiles de mascotas.
    Permite alternar entre las mascotas del tutor o desplegar el formulario para registrar una nueva.
    Si el tutor no tiene mascotas registradas, fuerza el modo de creación de nueva mascota.
    """
    is_new = request.GET.get('new', '').strip().lower() == 'true'

    # Resolver mascota activa y listado de mascotas del usuario
    active_pet_obj, user_pets = get_user_active_pet(request)
    pets_list = [serialize_pet_for_management(p) for p in user_pets]

    # Determinar si se presenta el formulario vacío de nueva mascota o la mascota activa
    if not user_pets:
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
def pet_save_view(request):
    """
    Guarda o actualiza la información del perfil de una mascota.
    Delega la persistencia a la capa de servicios y sincroniza la sesión activa.
    Redirige a la pantalla de gestión con mensaje de confirmación.
    """
    # Delegar la validación y persistencia de la mascota a la capa de servicios
    pet, _is_created = save_or_update_pet(request.user, request.POST, request.FILES)

    # Establecer la mascota guardada como activa en la cookie de sesión
    request.session['active_pet_id'] = str(pet.id)
    request.session.modified = True

    # Notificar al tutor y redirigir limpiamente sin parámetros en la URL
    messages.success(
        request, _('Los datos de %(name)s se guardaron exitosamente.') % {'name': pet.name}
    )
    return redirect('pets:pet_management')


@login_required
@require_POST
def pet_update_certificate_view(request):
    """
    Actualiza de forma asíncrona (AJAX / fetch) el tipo de certificado o pedigrí de una mascota.
    """
    data = parse_request_payload(request)
    pet_id = data.get('pet_id')
    certificate_val = str(data.get('certificate', '')).strip().lower()

    if not pet_id or not certificate_val:
        return JsonResponse(
            {'status': 'error', 'message': _('Parámetros incompletos.')},
            status=400,
        )

    # Delegar la actualización del certificado a la capa de servicios
    try:
        pet, clean_val, cert_label = update_pet_certificate(request.user, pet_id, certificate_val)
        return JsonResponse({
            'status': 'success',
            'message': _('Certificado actualizado correctamente.'),
            'pet_id': pet.id,
            'certificate': clean_val,
            'certificate_label': cert_label,
        })
    except Pet.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada o no pertenece al usuario actual.')},
            status=404,
        )


@login_required
@require_POST
def pet_toggle_goal_view(request):
    """
    Actualiza de forma asíncrona (AJAX / fetch) uno de los objetivos en PetMatch
    (is_matching, is_socializing o is_adoption) para la mascota del tutor.
    """
    data = parse_request_payload(request)
    pet_id = data.get('pet_id')
    goal = data.get('goal')
    value = data.get('value')

    if not pet_id or not goal:
        return JsonResponse(
            {'status': 'error', 'message': _('Parámetros incompletos.')},
            status=400,
        )

    is_enabled = value in (True, 'true', 'on', '1', 1)

    # Delegar la alternancia del objetivo a la capa de servicios
    try:
        pet = toggle_pet_goal(request.user, pet_id, goal, is_enabled)
        return JsonResponse({
            'status': 'success',
            'message': _('Objetivo actualizado correctamente.'),
            'pet_id': pet.id,
            'goal': goal,
            'value': is_enabled,
            'is_matching': pet.is_matching,
            'is_socializing': pet.is_socializing,
            'is_adoption': pet.is_adoption,
        })
    except Pet.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': _('Mascota no encontrada o no pertenece al usuario actual.')},
            status=404,
        )
    except ValueError as ve:
        return JsonResponse(
            {'status': 'error', 'message': str(ve)},
            status=400,
        )


@login_required
@require_POST
def pet_delete_view(request, pet_id):
    """
    Elimina de forma segura una mascota perteneciente al usuario autenticado.
    Verifica pertenencia y sincroniza la mascota activa restante en la sesión.
    """
    was_active = str(request.session.get('active_pet_id', '')) == str(pet_id)

    # Delegar la eliminación de la mascota a la capa de servicios
    try:
        pet_name, remaining_pet = delete_user_pet(request.user, pet_id)
    except Pet.DoesNotExist:
        messages.error(
            request,
            _('La mascota especificada no existe o no tienes permisos para eliminarla.'),
        )
        return redirect('pets:pet_management')

    # Reasignar la mascota activa en sesión si la eliminada era la activa
    if was_active:
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
    data = parse_request_payload(request)
    selected_id = str(data.get('selected_pet_id', '')).strip()
    next_url = data.get('next', '') or data.get('next_url', '') or request.GET.get('next', '')

    user_pets = list(Pet.objects.filter(owner=request.user).order_by('id'))
    if not user_pets:
        messages.info(
            request,
            _('Para comenzar la búsqueda de pareja, primero debes registrar a tu mascota.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    # Localizar la mascota seleccionada o usar la primera registrada
    active_pet = None
    if selected_id:
        target_str = selected_id.lower()
        active_pet = next(
            (p for p in user_pets if str(p.id) == target_str or p.name.lower() == target_str),
            None,
        )
    if not active_pet:
        active_pet = user_pets[0]

    # Guardar identificador en la cookie de sesión del usuario
    resolved_id = str(active_pet.id)
    request.session['active_pet_id'] = resolved_id
    request.session.modified = True

    # Almacenar filtro de preferencia de pedigrí en sesión
    pedigree_filter = str(data.get('pedigree_filter', 'both')).strip().lower()
    if pedigree_filter not in ('with_pedigree', 'without_pedigree', 'both'):
        pedigree_filter = 'both'
    request.session['match_pedigree_preference'] = pedigree_filter

    # Responder en formato JSON para peticiones asíncronas no originadas por formulario
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
    )
    if is_ajax and not data.get('is_form_submission'):
        return JsonResponse({'status': 'success', 'active_pet_id': resolved_id})

    # Redirigir a la URL siguiente solicitada si es segura
    if next_url and next_url.startswith('/'):
        return redirect(next_url)

    return redirect('pets:match_feed')


@login_required
def pet_select_view(request):
    """
    Renderiza la pantalla intermedia oficial de Selección de Mascota activa (reto 11, página 11)
    antes de avanzar hacia el flujo de emparejamiento (match feed).
    """
    # Resolver la mascota activa del tutor autenticado desde la sesión
    active_pet_obj, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request,
            _('Para comenzar la búsqueda de pareja y explorar pretendientes, primero debes registrar a tu mascota.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    # Obtener el contexto estructurado a través de la capa de servicios
    pedigree_preference = request.session.get('match_pedigree_preference', 'both')
    context = get_pet_select_context(request.user, active_pet_obj, user_pets, pedigree_preference)

    return render(request, 'pets/pet_select.html', context)


# ==============================================================================
# Vistas de Emparejamiento y Feed de Candidatos
# ==============================================================================


@login_required
def match_feed_view(request):
    """
    Renderiza la pantalla oficial de Buscar Pareja (feed de cruza/compatibilidad).
    Aplica el color de perfil personalizado de la mascota activa al contenedor de descubrimiento,
    soporta alternar candidatos dinámicos mediante el ORM y desplegar el diálogo modal interactivo de match.
    """
    # Resolver la mascota activa del tutor autenticado desde la sesión
    active_pet, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request, _('Debes registrar al menos una mascota para acceder al feed de parejas.')
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    # Validar que la mascota activa tenga habilitada la condición de búsqueda de pareja
    if not active_pet.is_active_for_match:
        messages.warning(
            request,
            _('La mascota activa %(name)s no tiene habilitada la búsqueda de pareja.')
            % {'name': active_pet.name},
        )
        return redirect('pets:pet_select')

    # Notificar si se recargó el feed o se restablecieron los filtros
    if request.GET.get('reload') == 'true':
        messages.info(request, _('El feed ha sido recargado con éxito.'))
    if request.GET.get('reset_filters') == 'true':
        messages.info(request, _('Los filtros han sido restablecidos.'))

    # Obtener el contexto estructurado a través de la capa de servicios
    context = get_match_feed_context(active_pet, user_pets, request.session, request.GET)

    return render(request, 'pets/match_feed.html', context)


@login_required
def match_interested_view(request):
    """
    Renderiza la pantalla oficial de Interesados - Solicitudes de emparejamiento y citas (UC-08.2).
    Permite al tutor revisar interesados, solicitudes enviadas, filtrar por pestañas y concertar citas.
    Delega la lógica de consulta y ordenamiento a la capa de servicios.
    """
    # Resolver la mascota activa del tutor autenticado desde la sesión
    active_pet, user_pets = get_user_active_pet(request)

    if not user_pets:
        messages.info(
            request,
            _('Debes registrar al menos una mascota antes de ver solicitudes e interesados.'),
        )
        return redirect(f"{reverse('pets:pet_management')}?new=true")

    # Obtener el contexto de solicitudes y citas a través de la capa de servicios
    tab = request.GET.get('tab', 'all')
    sort_by = request.GET.get('sort', 'compatibility')
    context = get_match_interested_context(active_pet, user_pets, tab=tab, sort_by=sort_by)

    return render(request, 'pets/match_interested.html', context)


# ==============================================================================
# Controladores Atómicos: Feed y Swipe de Candidatos
# ==============================================================================


@login_required
@require_POST
def match_like_candidate_view(request):
    """Registra interés hacia una mascota candidata del feed y evalúa coincidencia recíproca."""
    data = parse_request_payload(request)
    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return JsonResponse({'status': 'error', 'message': _('ID de candidato no especificado.')}, status=400)

    # Validar existencia del candidato en la base de datos
    try:
        candidate_pet = Pet.objects.get(id=candidate_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse({'status': 'error', 'message': _('Candidato no encontrado.')}, status=404)

    # Obtener la mascota activa del tutor desde la sesión
    active_pet, _user_pets = get_user_active_pet(request)
    if not active_pet:
        return JsonResponse({'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')}, status=400)

    # Validar que la mascota activa tenga activada la búsqueda de pareja
    if not active_pet.is_active_for_match:
        return JsonResponse({'status': 'error', 'message': _('La mascota activa no tiene habilitada la búsqueda de pareja.')}, status=400)

    # Evitar interacción entre mascotas del mismo dueño
    if candidate_pet.id == active_pet.id or candidate_pet.owner_id == request.user.id:
        return JsonResponse({'status': 'error', 'message': _('No puedes interactuar con tu propia mascota.')}, status=400)

    # Delegar el registro del like a la capa de servicios
    match_request, is_mutual = record_candidate_like(active_pet, candidate_pet)

    return JsonResponse({
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
    })


@login_required
@require_POST
def match_pass_candidate_view(request):
    """Registra el descarte de un candidato en el feed para avanzar a la siguiente tarjeta."""
    data = parse_request_payload(request)
    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return JsonResponse({'status': 'error', 'message': _('ID de candidato no especificado.')}, status=400)

    # Validar existencia del candidato
    try:
        candidate_pet = Pet.objects.get(id=candidate_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse({'status': 'error', 'message': _('Candidato no encontrado.')}, status=404)

    # Obtener la mascota activa del tutor desde la sesión
    active_pet, _user_pets = get_user_active_pet(request)
    if not active_pet:
        return JsonResponse({'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')}, status=400)

    # Delegar el registro del descarte a la capa de servicios
    match_request = record_candidate_pass(active_pet, candidate_pet)

    return JsonResponse({
        'status': 'success',
        'candidate_id': candidate_pet.id,
        'match_request_id': match_request.id,
    })


@login_required
@require_POST
def match_report_candidate_view(request):
    """Registra una denuncia o reporte contra una mascota candidata desde el feed."""
    data = parse_request_payload(request)
    reported_pet_id = data.get('candidate_id') or data.get('reported_pet_id')
    reason = data.get('reason', '').strip()

    if not reported_pet_id:
        return JsonResponse({'status': 'error', 'message': _('ID de mascota candidata no especificado.')}, status=400)

    # Validar existencia de la mascota reportada
    try:
        reported_pet = Pet.objects.get(id=reported_pet_id)
    except (Pet.DoesNotExist, ValueError):
        return JsonResponse({'status': 'error', 'message': _('Mascota candidata no encontrada.')}, status=404)

    # Delegar la creación del reporte a la capa de servicios
    report = report_candidate_pet(
        reporter_user=request.user,
        reported_pet=reported_pet,
        reason=reason,
    )

    # Descartar automáticamente a la mascota reportada para que no vuelva a aparecer en el feed
    active_pet, _user_pets = get_user_active_pet(request)
    if active_pet:
        record_candidate_pass(active_pet, reported_pet)

    return JsonResponse({
        'status': 'success',
        'report_id': report.id,
        'message': _('El reporte ha sido enviado al equipo de administración para su revisión.'),
    })


# ==============================================================================
# Siluetas de Controladores: Solicitudes e Interesados
# ==============================================================================


@login_required
@require_POST
def match_accept_request_view(request, request_id):
    """Acepta una solicitud de match recibida en la bandeja de interesados."""
    # Obtener la mascota activa del tutor
    active_pet, _user_pets = get_user_active_pet(request)
    if not active_pet:
        return JsonResponse({'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')}, status=400)

    # Delegar la aceptación de la solicitud a la capa de servicios
    try:
        match_request = accept_match_request(request_id=request_id, active_pet=active_pet)
        tab_counters = get_requests_tab_counters(active_pet)
        return JsonResponse({
            'status': 'success',
            'match_status': 'accepted',
            'request_id': match_request.id,
            'message': _('Solicitud de match aceptada exitosamente.'),
            'tab_counters': tab_counters,
        })
    except MatchRequest.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('La solicitud de match no existe o no corresponde a tu mascota activa.'),
        }, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def match_reject_request_view(request, request_id):
    """Descarta o rechaza una solicitud de match en la bandeja de interesados."""
    # Obtener la mascota activa del tutor
    active_pet, _user_pets = get_user_active_pet(request)
    if not active_pet:
        return JsonResponse({'status': 'error', 'message': _('No se encontró una mascota activa para el usuario.')}, status=400)

    # Delegar el rechazo de la solicitud a la capa de servicios
    try:
        match_request = reject_match_request(request_id=request_id, active_pet=active_pet)
        tab_counters = get_requests_tab_counters(active_pet)
        return JsonResponse({
            'status': 'success',
            'match_status': 'rejected',
            'request_id': match_request.id,
            'message': _('Solicitud descartada exitosamente.'),
            'tab_counters': tab_counters,
        })
    except MatchRequest.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('La solicitud de match no existe o no corresponde a tu mascota activa.'),
        }, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def send_initial_note_view(request, request_id):
    """
    Registra o actualiza la nota inicial de contacto tras un match aceptado
    o durante la interacción con una solicitud de match.
    """
    data = parse_request_payload(request)
    note_text = (
        data.get('note')
        or data.get('notes')
        or data.get('note_text')
        or data.get('message')
        or data.get('initial_message', '')
    )
    clean_note = str(note_text).strip()

    if not clean_note:
        return JsonResponse({'status': 'error', 'message': _('La nota no puede estar vacía.')}, status=400)

    # Delegar el guardado de la nota a la capa de servicios
    try:
        result = send_initial_match_note(
            request_id=request_id,
            sender_user=request.user,
            note_text=clean_note,
        )
        return JsonResponse(result)
    except MatchRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': _('La solicitud de match no fue encontrada.')}, status=404)
    except PermissionError as pe:
        return JsonResponse({'status': 'error', 'message': str(pe)}, status=403)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ==============================================================================
# Siluetas de Controladores: Citas y Encuentros Caninos
# ==============================================================================


@login_required
@require_POST
def schedule_meetup_view(request):
    """Procesa la concertación de un encuentro canino seguro desde el modal interactivo."""
    data = parse_request_payload(request)
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

    # Identificar la mascota solicitante del usuario
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

    # Identificar la mascota destinataria del encuentro
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

    # Delegar la persistencia de la cita a la capa de servicios
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
    """Cancela una cita de encuentro canino previamente acordada."""
    data = parse_request_payload(request)
    reason = str(data.get('reason', '')).strip()

    # Delegar la cancelación a la capa de servicios
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
