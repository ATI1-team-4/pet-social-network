"""
Capa de servicios y lógica de negocio para la aplicación pets.

Define las siluetas de las funciones especializadas para:
- Descubrimiento y evaluación de candidatos en el feed de emparejamiento (#63).
- Gestión de solicitudes e interesados en el emparejamiento (#64).
- Concertación de citas y agenda de encuentros seguros (#65).
"""

import json
import math
from datetime import date, datetime, time
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, F, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import UserReport
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


def get_user_pets(user_id: Any) -> list[Any]:
    """Obtiene el listado de mascotas pertenecientes a un tutor."""
    return list(Pet.objects.filter(owner_id=user_id).order_by('id'))


# ==============================================================================
# Servicios de Apoyo: Cálculo de Distancia y Compatibilidad
# ==============================================================================


def calculate_candidate_distance_km(active_pet: Pet, candidate_pet: Pet) -> float:
    """
    Calcula la distancia real en kilómetros (float) entre los tutores de ambas mascotas
    utilizando la fórmula de Haversine sobre sus coordenadas GPS (latitud y longitud).
    Si faltan coordenadas, retorna una estimación por municipio o defecto.
    """
    p1 = getattr(active_pet.owner, 'profile', None)
    p2 = getattr(candidate_pet.owner, 'profile', None)

    if (
        p1
        and p2
        and p1.latitude is not None
        and p1.longitude is not None
        and p2.latitude is not None
        and p2.longitude is not None
    ):
        lat1, lon1 = float(p1.latitude), float(p1.longitude)
        lat2, lon2 = float(p2.latitude), float(p2.longitude)
        radius = 6371.0  # Radio terrestre en km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
        return round(radius * c, 1)

    if p1 and p2 and p1.municipality and p2.municipality:
        if p1.municipality.lower() == p2.municipality.lower():
            return 1.5
        if p1.state and p2.state and p1.state.lower() == p2.state.lower():
            return 4.2

    return 2.5


def calculate_candidate_distance(active_pet: Pet, candidate_pet: Pet) -> str:
    """
    Calcula una distancia legible en km entre los tutores de ambas mascotas
    a partir de sus coordenadas GPS.
    """
    km = calculate_candidate_distance_km(active_pet, candidate_pet)
    if km < 0.5:
        return _('A menos de 500 m')
    elif km < 1.0:
        return _('A menos de 1 km')
    return _('A %(km)s km') % {'km': km}


def calculate_candidate_compatibility(active_pet: Pet, candidate_pet: Pet) -> int:
    """
    Calcula el porcentaje de afinidad simple basado exclusivamente
    en la especie, el sexo de la mascota y la coincidencia de raza:
    - Distinta especie: 0%
    - Misma especie + Sexo opuesto + Misma raza: 95%
    - Misma especie + Sexo opuesto + Distinta raza: 75%
    - Misma especie + Mismo sexo + Misma raza: 60%
    - Misma especie + Mismo sexo + Distinta raza: 50%
    """
    # Especie: Deben pertenecer a la misma especie
    same_species = False
    if getattr(active_pet, 'species_id', None) and getattr(candidate_pet, 'species_id', None):
        same_species = active_pet.species_id == candidate_pet.species_id
    elif getattr(active_pet, 'species', None) and getattr(candidate_pet, 'species', None):
        s1 = getattr(active_pet.species, 'slug', None) or str(active_pet.species).lower()
        s2 = getattr(candidate_pet.species, 'slug', None) or str(candidate_pet.species).lower()
        same_species = s1 == s2

    if not same_species:
        return 0

    # Sexo: Compatibilidad biológica (opuesto vs mismo sexo)
    is_opposite_sex = (
        (active_pet.is_macho and candidate_pet.is_hembra)
        or (active_pet.is_hembra and candidate_pet.is_macho)
        or (active_pet.gender != candidate_pet.gender)
    )

    # Raza: Coincidencia exacta de raza
    same_breed = bool(
        active_pet.breed
        and candidate_pet.breed
        and active_pet.breed.strip().lower() == candidate_pet.breed.strip().lower()
    )

    if is_opposite_sex:
        return 95 if same_breed else 75
    return 60 if same_breed else 50


def serialize_candidate(active_pet: Pet, candidate_pet: Pet) -> dict[str, Any]:
    """
    Serializa una instancia de `Pet` candidata a un diccionario estructurado
    para alimentar el contexto del feed y la variable interactiva `candidates_json`.
    """
    compat = calculate_candidate_compatibility(active_pet, candidate_pet)
    dist = calculate_candidate_distance(active_pet, candidate_pet)
    owner = candidate_pet.owner
    owner_profile = getattr(owner, 'profile', None)

    # Iniciales del tutor para el avatar
    tutor_name = owner.get_full_name() or owner.username
    parts = tutor_name.split()
    avatar_initials = (
        (parts[0][0] + (parts[1][0] if len(parts) > 1 else '')).upper() if parts else 'TU'
    )

    tutor_rating = '5.0'
    tutor_reviews = _('0 citas')
    if owner_profile:
        tutor_rating = str(owner_profile.rating)
        meetings = owner_profile.completed_meetings_count
        if meetings == 1:
            tutor_reviews = _('1 cita')
        else:
            tutor_reviews = _('%(count)s citas') % {'count': meetings}

    birth_str = (
        candidate_pet.birth_date.strftime('%d / %b / %Y')
        if candidate_pet.birth_date
        else _('No especificada')
    )
    weight_str = (
        f'{candidate_pet.weight_kg} kg' if candidate_pet.weight_kg else _('No especificado')
    )
    if candidate_pet.has_pedigree:
        cert_str = (
            candidate_pet.certificate_number
            or candidate_pet.certificate_type
            or _('Certificado FCI')
        )
        cert_label = str(candidate_pet.certificate_type or _('Certificado FCI'))
    else:
        cert_str = candidate_pet.certificate_type or _('Sin pedigrí')
        cert_label = str(candidate_pet.certificate_type or _('Sin pedigrí'))

    return {
        'id': candidate_pet.id,
        'name': candidate_pet.name,
        'gender': candidate_pet.gender,
        'gender_label': str(candidate_pet.gender_label),
        'gender_icon': candidate_pet.gender_icon,
        'is_hembra': candidate_pet.is_hembra,
        'is_macho': candidate_pet.is_macho,
        'species': candidate_pet.species.slug if candidate_pet.species else 'perro',
        'species_label': str(candidate_pet.species_label),
        'breed': candidate_pet.breed,
        'breed_short': candidate_pet.breed.split('(')[0].strip(),
        'age': str(candidate_pet.age_text),
        'birth_date': birth_str,
        'weight': weight_str,
        'certificate': cert_str,
        'certificate_label': cert_label,
        'has_pedigree': candidate_pet.has_pedigree,
        'compatibility_num': compat,
        'compatibility': f'{compat}%',
        'distance': dist,
        'location': candidate_pet.location,
        'purpose': str(candidate_pet.get_purpose_display()),
        'profile_color': candidate_pet.profile_color,
        'profile_color_hex': candidate_pet.profile_color_hex,
        'photo_url': candidate_pet.photo_url,
        'photo_clean_url': candidate_pet.photo_clean_url,
        'temperaments': candidate_pet.temperament_list or [_('Sociable'), _('Juguetón')],
        'description': candidate_pet.description
        or _('Mascota amistosa en busca de nuevos amigos y compañía.'),
        'tutors': {
            'name': tutor_name,
            'location': candidate_pet.location,
            'rating': tutor_rating,
            'review_count': tutor_reviews,
            'avatar_letter': avatar_initials,
        },
    }


# ==============================================================================
# Servicios para Feed y Descubrimiento de Candidatos (Issue #63)
# ==============================================================================


def get_match_candidates(
    active_pet: Pet, filters: Optional[dict[str, Any]] = None
) -> QuerySet[Pet]:
    """
    Consulta mediante el ORM candidatos compatibles para el feed de emparejamiento.
    - Filtra por sexo opuesto (`gender != active_pet.gender`).
    - Excluye a la propia mascota activa y mascotas del mismo tutor.
    - Excluye candidatos previamente evaluados (likes salientes o descartes registrados en MatchRequest).
    - Asegura que `is_active_for_match = True`.
    - Prioriza y recomienda candidatos de la misma raza primero.
    """
    opposite_gender = Pet.Gender.HEMBRA if active_pet.is_macho else Pet.Gender.MACHO

    # Candidatos ya evaluados por la mascota activa (interés previo o descarte)
    evaluated_ids = set(
        MatchRequest.objects.filter(from_pet=active_pet).values_list('to_pet_id', flat=True)
    )
    # Candidatos con solicitudes ya resueltas (aceptadas o rechazadas) hacia la mascota activa
    already_resolved_ids = set(
        MatchRequest.objects.filter(
            to_pet=active_pet,
            status__in=[MatchRequest.RequestStatus.ACCEPTED, MatchRequest.RequestStatus.REJECTED],
        ).values_list('from_pet_id', flat=True)
    )
    excluded_ids = evaluated_ids.union(already_resolved_ids)

    queryset = (
        Pet.objects.filter(
            is_active_for_match=True,
            gender=opposite_gender,
        )
        .exclude(id=active_pet.id)
        .exclude(owner=active_pet.owner)
        .exclude(id__in=excluded_ids)
        .select_related('species', 'owner', 'owner__profile')
    )

    if active_pet.species_id:
        queryset = queryset.filter(species_id=active_pet.species_id)

    if filters:
        if filters.get('breed'):
            queryset = queryset.filter(breed__icontains=filters['breed'])
        if filters.get('has_pedigree'):
            queryset = queryset.filter(has_pedigree=True)
        elif filters.get('without_pedigree'):
            queryset = queryset.filter(has_pedigree=False)
        if filters.get('purpose') and filters['purpose'] != 'all':
            if filters['purpose'] == 'both':
                queryset = queryset.filter(purpose=Pet.Purpose.BOTH)
            elif filters['purpose'] == 'mating':
                queryset = queryset.filter(purpose=Pet.Purpose.MATING)
            elif filters['purpose'] == 'play':
                queryset = queryset.filter(purpose__in=[Pet.Purpose.PLAY, Pet.Purpose.BOTH])
            else:
                queryset = queryset.filter(purpose=filters['purpose'])
        if filters.get('max_distance') is not None:
            try:
                max_dist = float(filters['max_distance'])
                eligible_ids = [
                    cand.id
                    for cand in queryset
                    if calculate_candidate_distance_km(active_pet, cand) <= max_dist
                ]
                queryset = queryset.filter(id__in=eligible_ids)
            except (ValueError, TypeError):
                pass

    # Recomendación por raza: candidatos de la misma raza primero
    return queryset.order_by(
        Case(
            When(breed__iexact=active_pet.breed, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
        'name',
    )


def record_candidate_like(active_pet: Pet, candidate_pet: Pet) -> tuple[MatchRequest, bool]:
    """
    Registra el interés ('Me gusta') hacia un candidato del feed y evalúa coincidencia recíproca.
    - Si el candidato ya había manifestado interés previo hacia `active_pet`,
      ambas solicitudes transicionan a `ACCEPTED` y retorna `(match_request, is_mutual=True)`.
    - De lo contrario, crea o actualiza `MatchRequest` en estado `PENDING` y retorna `is_mutual=False`.
    """
    if active_pet.id == candidate_pet.id or active_pet.owner_id == candidate_pet.owner_id:
        raise ValueError(_('No puedes dar me gusta a tus propias mascotas ni a la misma mascota.'))

    reverse_request = MatchRequest.objects.filter(
        from_pet=candidate_pet,
        to_pet=active_pet,
    ).first()

    if reverse_request and reverse_request.status != MatchRequest.RequestStatus.REJECTED:
        reverse_request.status = MatchRequest.RequestStatus.ACCEPTED
        reverse_request.save(update_fields=['status', 'updated_at'])

        match_request, _created = MatchRequest.objects.update_or_create(
            from_pet=active_pet,
            to_pet=candidate_pet,
            defaults={
                'status': MatchRequest.RequestStatus.ACCEPTED,
                'notes': _('Match mutuo confirmado en el feed de descubrimiento.'),
            },
        )
        return match_request, True

    match_request, _created = MatchRequest.objects.update_or_create(
        from_pet=active_pet,
        to_pet=candidate_pet,
        defaults={
            'status': MatchRequest.RequestStatus.PENDING,
            'notes': _('Interés registrado desde el feed de descubrimiento.'),
        },
    )
    return match_request, False


def record_candidate_pass(active_pet: Pet, candidate_pet: Pet) -> MatchRequest:
    """
    Registra el descarte de un candidato en el feed para excluirlo de futuras recomendaciones.
    Crea o actualiza la solicitud saliente con estado `REJECTED`.
    """
    if active_pet.id == candidate_pet.id or active_pet.owner_id == candidate_pet.owner_id:
        raise ValueError(_('No puedes descartar a tus propias mascotas ni a la misma mascota.'))

    match_request, _created = MatchRequest.objects.update_or_create(
        from_pet=active_pet,
        to_pet=candidate_pet,
        defaults={
            'status': MatchRequest.RequestStatus.REJECTED,
            'notes': _('Candidato descartado en el feed de descubrimiento.'),
        },
    )
    return match_request


def report_candidate_pet(
    reporter_user: Any,
    reported_pet: Pet,
    reason: str,
    admin_notes: str = '',
) -> UserReport:
    """
    Registra una denuncia o reporte contra una mascota candidata o su tutor en `UserReport`.
    """
    clean_reason = (
        reason.strip()
        if reason and reason.strip()
        else _('Contenido o conducta inapropiada en el feed.')
    )
    report = UserReport.objects.create(
        reported_by=reporter_user,
        reported_user=reported_pet.owner,
        reported_pet=reported_pet,
        reason=clean_reason,
        status=UserReport.ReportStatus.PENDING,
        admin_notes=admin_notes,
    )
    return report


# ==============================================================================
# Siluetas de Servicio para Solicitudes e Interesados (Issue #64)
# ==============================================================================


def get_interested_match_requests(
    active_pet: Optional[Pet], status: Optional[str] = None
) -> QuerySet[MatchRequest]:
    """
    Obtiene las solicitudes de match recibidas hacia la mascota activa (Interesados).
    Optimizado con select_related y orden descendente por fecha de creación.
    Excluye solicitudes rechazadas por defecto salvo que se especifique un estado.
    Garantiza que no aparezcan mascotas del mismo dueño.
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(to_pet=active_pet)
        .exclude(from_pet__owner=active_pet.owner)
        .select_related('from_pet', 'from_pet__owner', 'from_pet__owner__profile')
        .order_by('-created_at')
    )
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status=MatchRequest.RequestStatus.REJECTED)
    return qs


def get_sent_match_requests(
    active_pet: Optional[Pet], status: Optional[str] = None
) -> QuerySet[MatchRequest]:
    """
    Obtiene las solicitudes de match enviadas por la mascota activa hacia otros candidatos.
    Optimizado con select_related y orden descendente por fecha de creación.
    Excluye solicitudes rechazadas por defecto salvo que se especifique un estado.
    Garantiza que no aparezcan mascotas del mismo dueño.
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(from_pet=active_pet)
        .exclude(to_pet__owner=active_pet.owner)
        .select_related('to_pet', 'to_pet__owner', 'to_pet__owner__profile')
        .order_by('-created_at')
    )
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status=MatchRequest.RequestStatus.REJECTED)
    return qs


def get_all_match_requests_for_pet(
    active_pet: Optional[Pet], status: Optional[str] = None
) -> QuerySet[MatchRequest]:
    """
    Obtiene todas las solicitudes de match (recibidas y enviadas) asociadas a la mascota activa.
    Excluye solicitudes rechazadas por defecto salvo que se especifique un estado.
    Garantiza que no aparezcan mascotas del mismo dueño.
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(Q(to_pet=active_pet) | Q(from_pet=active_pet))
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
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status=MatchRequest.RequestStatus.REJECTED)
    return qs


def get_requests_tab_counters(active_pet: Optional[Pet]) -> dict[str, int]:
    """
    Calcula dinámicamente los contadores de solicitudes para las pestañas de la bandeja:
    - 'all': Total de solicitudes activas (recibidas y enviadas).
    - 'interested': Solicitudes recibidas activas hacia la mascota activa.
    - 'sent': Solicitudes enviadas por la mascota activa.
    - 'pending': Solicitudes recibidas pendientes de respuesta.
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return {
            'all': 0,
            'interested': 0,
            'sent': 0,
            'pending': 0,
        }

    received_qs = get_interested_match_requests(active_pet)
    sent_qs = get_sent_match_requests(active_pet)
    all_qs = get_all_match_requests_for_pet(active_pet)

    interested_count = received_qs.count()
    sent_count = sent_qs.count()
    pending_count = received_qs.filter(status=MatchRequest.RequestStatus.PENDING).count()
    matches_count = all_qs.filter(status=MatchRequest.RequestStatus.ACCEPTED).count()
    all_count = all_qs.count()

    return {
        'all': all_count,
        'interested': interested_count,
        'sent': sent_count,
        'pending': pending_count,
        'matches': matches_count,
    }


def accept_match_request(request_id: int, active_pet: Pet) -> MatchRequest:
    """
    Acepta una solicitud de match recibida.
    Valida que la solicitud pertenezca a `to_pet == active_pet` y actualiza a ACCEPTED.
    Si existe solicitud recíproca, la actualiza para consolidar el match mutuo.
    """
    match_request = MatchRequest.objects.select_related('from_pet', 'to_pet').get(
        id=request_id,
        to_pet=active_pet,
    )
    match_request.status = MatchRequest.RequestStatus.ACCEPTED
    match_request.save(update_fields=['status', 'updated_at'])

    # Si existe solicitud inversa previa, sincronizarla como aceptada
    MatchRequest.objects.filter(
        from_pet=active_pet,
        to_pet=match_request.from_pet,
    ).exclude(status=MatchRequest.RequestStatus.REJECTED).update(
        status=MatchRequest.RequestStatus.ACCEPTED
    )

    return match_request


def reject_match_request(request_id: int, active_pet: Pet) -> MatchRequest:
    """
    Rechaza o descarta una solicitud o cancela un match en la bandeja.
    Valida que pertenezca a la mascota activa (como destinataria o remitente) y actualiza a REJECTED.
    Si el match estaba aceptado, sincroniza la solicitud inversa y cancela citas asociadas.
    """
    match_request = MatchRequest.objects.select_related('from_pet', 'to_pet').get(
        Q(to_pet=active_pet) | Q(from_pet=active_pet),
        id=request_id,
    )
    was_accepted = match_request.status == MatchRequest.RequestStatus.ACCEPTED
    match_request.status = MatchRequest.RequestStatus.REJECTED
    match_request.save(update_fields=['status', 'updated_at'])

    if was_accepted:
        # Sincronizar solicitud inversa para coherencia bidireccional
        other_pet = (
            match_request.to_pet if match_request.from_pet == active_pet else match_request.from_pet
        )
        MatchRequest.objects.filter(
            from_pet=other_pet,
            to_pet=active_pet,
        ).update(status=MatchRequest.RequestStatus.REJECTED)

        # Cancelar citas asociadas pendientes o confirmadas si las hubiera
        PetMeetup.objects.filter(
            match_request=match_request,
            status__in=[PetMeetup.MeetupStatus.PROPOSED, PetMeetup.MeetupStatus.CONFIRMED],
        ).update(status=PetMeetup.MeetupStatus.CANCELLED)

    return match_request


def send_initial_match_note(
    request_id: int,
    sender_user: Any,
    note_text: str,
) -> dict[str, Any]:
    """
    Registra o actualiza la nota de contacto asociada a la solicitud en `MatchRequest.notes`.
    Valida permisos del usuario remitente sobre la solicitud.
    """
    clean_note = (note_text or '').strip()
    if not clean_note:
        raise ValueError(_('El texto del mensaje o nota no puede estar vacío.'))

    match_request = MatchRequest.objects.select_related('from_pet', 'to_pet').get(
        id=request_id,
    )
    if (
        match_request.from_pet.owner_id != sender_user.id
        and match_request.to_pet.owner_id != sender_user.id
    ):
        raise PermissionError(_('No tienes permiso para agregar notas a esta solicitud.'))

    match_request.notes = clean_note
    match_request.save(update_fields=['notes', 'updated_at'])

    return {
        'status': 'success',
        'request_id': match_request.id,
        'notes': match_request.notes,
        'message': _('Nota guardada exitosamente.'),
    }


def get_translated_certificate(cert_str: str, has_pedigree: bool) -> str:
    """Retorna la etiqueta traducible de certificación de la mascota."""
    if not cert_str and not has_pedigree:
        return ''
    raw = (cert_str or '').strip()
    raw_lower = raw.lower()
    if 'pedigr' in raw_lower or 'fci' in raw_lower:
        return _('Pedigrí certificado')
    elif 'tramite' in raw_lower or 'trámite' in raw_lower:
        return _('En trámite')
    elif 'sin' in raw_lower:
        return _('Sin pedigrí')
    elif has_pedigree:
        return _('Pedigrí certificado')
    return _(raw)


def serialize_match_request(active_pet: Pet, req: MatchRequest) -> dict[str, Any]:
    """
    Serializa un registro real de `MatchRequest` para su renderizado en la plantilla `match_interested.html`.
    Extrae atributos del candidato (remitente si es recibida, destinatario si es enviada).
    """
    is_received = req.to_pet_id == active_pet.id
    candidate = req.from_pet if is_received else req.to_pet

    # Estimación de compatibilidad con la mascota activa
    match_pct = calculate_candidate_compatibility(active_pet, candidate)

    category = 'breeding' if candidate.is_matching else 'social'

    if req.status == MatchRequest.RequestStatus.ACCEPTED:
        badge_label = _('Match aceptado')
    elif is_received:
        badge_label = _('Interesado en %(name)s') % {'name': active_pet.name}
    else:
        badge_label = _('Solicitud enviada')

    tutor = candidate.owner
    tutor_full_name = tutor.get_full_name().strip() if hasattr(tutor, 'get_full_name') else ''
    if not tutor_full_name:
        tutor_full_name = tutor.username
    tutor_signature = _('%(name)s (Tutor de %(pet)s)') % {
        'name': tutor_full_name,
        'pet': candidate.name,
    }

    if is_received:
        # Petición recibida hacia active_pet: la nota fue redactada por el tutor solicitante
        raw_note = req.notes
        if raw_note and 'Interés registrado desde el feed' in raw_note:
            card_quote = _('Interés registrado desde el feed de descubrimiento.')
        elif raw_note:
            card_quote = raw_note
        elif candidate.description:
            card_quote = candidate.description
        else:
            card_quote = _('Interesado en conectar y evaluar compatibilidad.')
        sent_note = ''
    else:
        # Petición enviada desde active_pet hacia candidate:
        # En la tarjeta del candidato debe aparecer la nota / presentación del candidato a quien se le envió el match
        if candidate.description:
            card_quote = candidate.description
        else:
            card_quote = _('Mascota disponible para conectar y evaluar compatibilidad.')
        sent_note = req.notes or ''

    # Traducción dinámica de rasgos de temperamento
    translated_temperaments = []
    for trait in candidate.temperament_list:
        clean_trait = trait.strip()
        tl = clean_trait.lower()
        if tl in ('sociable',):
            translated_temperaments.append(_('Sociable'))
        elif tl in ('jugueton', 'juguetón'):
            translated_temperaments.append(_('Juguetón'))
        elif tl in ('carinoso', 'cariñoso'):
            translated_temperaments.append(_('Cariñoso'))
        elif tl in ('tranquila', 'tranquilo'):
            translated_temperaments.append(_('Tranquila'))
        elif tl in ('calmada', 'calmado'):
            translated_temperaments.append(_('Calmada'))
        elif tl in ('curiosa', 'curioso'):
            translated_temperaments.append(_('Curiosa'))
        elif tl in ('inteligente',):
            translated_temperaments.append(_('Inteligente'))
        elif tl in ('mimosa', 'mimoso'):
            translated_temperaments.append(_('Mimosa'))
        elif tl in ('silenciosa', 'silencioso'):
            translated_temperaments.append(_('Silenciosa'))
        else:
            translated_temperaments.append(_(clean_trait))

    if not translated_temperaments:
        translated_temperaments = [_('Sociable'), _('Juguetón')]

    is_recent = True
    recent_label = _('Nueva solicitud')
    if req.created_at:
        diff = timezone.now() - req.created_at
        if diff.days >= 1:
            is_recent = False
            recent_label = _('Hace %(days)s d') % {'days': diff.days}
        elif diff.seconds >= 3600:
            recent_label = _('Hace %(hours)s h') % {'hours': diff.seconds // 3600}
        else:
            recent_label = _('Hace unos minutos')

    return {
        'id': req.id,
        'request_id': req.id,
        'candidate_pet_id': candidate.id,
        'name': candidate.name,
        'gender': 'hembra' if candidate.is_hembra else 'macho',
        'gender_icon': candidate.gender_icon,
        'is_hembra': candidate.is_hembra,
        'breed': candidate.breed,
        'species_label': str(candidate.species_label),
        'age': str(candidate.age_text),
        'birth_date': candidate.birth_date.strftime('%d/%m/%Y') if candidate.birth_date else '',
        'certificate': get_translated_certificate(
            candidate.certificate_type, candidate.has_pedigree
        ),
        'distance': calculate_candidate_distance(active_pet, candidate),
        'distance_val': calculate_candidate_distance_km(active_pet, candidate),
        'location': candidate.location,
        'match_percentage': f'{match_pct}%',
        'compatibility_val': match_pct,
        'category': category,
        'is_recent': is_recent,
        'recent_label': recent_label,
        'badge_label': badge_label,
        'photo_url': candidate.photo_url,
        'temperaments': translated_temperaments,
        'quote': card_quote,
        'sent_note': sent_note,
        'tutor_name': tutor_full_name,
        'tutor_signature': tutor_signature,
        'status': req.status,
        'status_label': req.get_status_display(),
        'is_received': is_received,
        'is_sent': not is_received,
        'is_sent_num': 1 if not is_received else 0,
        'action_type': 'match'
        if req.status == MatchRequest.RequestStatus.ACCEPTED
        else ('sent' if not is_received else 'received'),
        'type': 'interested' if is_received else 'sent',
        'created_at': req.created_at,
        'created_timestamp': int(req.created_at.timestamp()) if req.created_at else 0,
    }


# ==============================================================================
# Siluetas de Servicio para Encuentros y Citas Seguras (Issue #65)
# ==============================================================================


def get_upcoming_pet_meetups(active_pet: Optional[Pet]) -> QuerySet[PetMeetup]:
    """
    Obtiene las citas confirmadas o propuestas próximas para la barra lateral.
    Filtra por fecha futura o de hoy (`date >= date.today()`) y ordena cronológicamente.
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return PetMeetup.objects.none()
    return (
        PetMeetup.objects.filter(Q(host_pet=active_pet) | Q(guest_pet=active_pet))
        .exclude(host_pet__owner=F('guest_pet__owner'))
        .filter(
            date__gte=date.today(),
            status__in=[PetMeetup.MeetupStatus.CONFIRMED, PetMeetup.MeetupStatus.PROPOSED],
        )
        .select_related('host_pet', 'guest_pet', 'host_pet__owner', 'guest_pet__owner')
        .order_by('date', 'time')
    )


def serialize_pet_meetup(active_pet: Pet, meetup: PetMeetup) -> dict[str, Any]:
    """
    Serializa un encuentro de PetMeetup para su renderizado en la barra lateral de citas confirmadas.
    """
    other_pet = meetup.guest_pet if meetup.host_pet_id == active_pet.id else meetup.host_pet
    time_str = meetup.time.strftime('%I:%M %p') if meetup.time else ''
    scheduled_by_user = meetup.scheduled_by
    scheduled_by_name = (
        scheduled_by_user.get_full_name() or scheduled_by_user.username
        if scheduled_by_user
        else ''
    )
    return {
        'id': f'meetup-{meetup.id}',
        'meetup_id': meetup.id,
        'badge': meetup.get_status_display(),
        'day': meetup.date.strftime('%d/%m/%Y'),
        'title': f'{_("Cita con")} {other_pet.name}',
        'pet_name': other_pet.name,
        'location': meetup.location_name or _('Espacio canino verificado'),
        'time': time_str,
        'status': meetup.status,
        'notes': meetup.notes,
        'scheduled_by': scheduled_by_name,
    }


def schedule_pet_meetup(
    requester_user: Any,
    requester_pet: Pet,
    target_pet: Pet,
    meeting_date: date,
    meeting_time: time,
    location_name: str,
    location_address: str = '',
    notes: str = '',
    status: str = PetMeetup.MeetupStatus.CONFIRMED,
) -> PetMeetup:
    """
    Persiste la concertación de una nueva cita de socialización o cruza responsable en PetMeetup.

    Requerimientos:
    - Validar que `requester_pet.owner == requester_user`.
    - Validar que no sea la misma mascota.
    - Validar que la fecha y hora sean futuras.
    - Validar disponibilidad temporal (sin solapamiento exacto de cita activa).
    - Asociar la solicitud de match existente (si la hay).
    - Crear instancia en `PetMeetup` con estado `confirmed` (o el indicado).
    """
    if requester_pet.owner_id != requester_user.id and requester_pet.owner != requester_user:
        raise PermissionError(_('El usuario no es el tutor de la mascota solicitante.'))

    if requester_pet.id == target_pet.id or requester_pet.owner_id == target_pet.owner_id:
        raise ValueError(
            _(
                'No se puede programar un encuentro entre mascotas del mismo tutor ni con la misma mascota.'
            )
        )

    now = timezone.localtime() if timezone.is_aware(timezone.now()) else datetime.now()
    meeting_dt = datetime.combine(meeting_date, meeting_time)
    if timezone.is_aware(now):
        meeting_dt = timezone.make_aware(meeting_dt, timezone.get_current_timezone())

    if meeting_dt <= now:
        raise ValueError(_('La fecha y hora del encuentro deben ser futuras.'))

    active_statuses = [
        PetMeetup.MeetupStatus.CONFIRMED,
        PetMeetup.MeetupStatus.PROPOSED,
    ]

    has_conflict = PetMeetup.objects.filter(
        Q(host_pet__in=[requester_pet, target_pet]) | Q(guest_pet__in=[requester_pet, target_pet]),
        date=meeting_date,
        time=meeting_time,
        status__in=active_statuses,
    ).exists()

    if has_conflict:
        raise ValueError(
            _(
                'Una de las mascotas ya tiene un encuentro programado para esa misma fecha y hora. '
                'Por favor selecciona otro horario.'
            )
        )

    # Vincular MatchRequest correspondiente si existe
    match_req = MatchRequest.objects.filter(
        Q(from_pet=requester_pet, to_pet=target_pet) | Q(from_pet=target_pet, to_pet=requester_pet)
    ).first()

    meetup = PetMeetup.objects.create(
        match_request=match_req,
        host_pet=requester_pet,
        guest_pet=target_pet,
        date=meeting_date,
        time=meeting_time,
        location_name=location_name,
        notes=notes,
        status=status,
    )
    return meetup


def cancel_pet_meetup(meetup_id: int, user: Any, reason: str = '') -> PetMeetup:
    """
    Cancela una cita de encuentro previamente acordada.

    Requerimientos:
    - Validar que el usuario sea tutor de `host_pet` o de `guest_pet` (o staff).
    - Actualizar estado de `PetMeetup` a `CANCELLED`.
    - Retornar la instancia cancelada.
    """
    meetup = PetMeetup.objects.select_related(
        'host_pet', 'guest_pet', 'host_pet__owner', 'guest_pet__owner'
    ).get(id=meetup_id)

    is_host_owner = meetup.host_pet.owner_id == user.id or meetup.host_pet.owner == user
    is_guest_owner = meetup.guest_pet.owner_id == user.id or meetup.guest_pet.owner == user
    is_staff = getattr(user, 'is_staff', False)

    if not (is_host_owner or is_guest_owner or is_staff):
        raise PermissionError(_('No tienes permiso para cancelar esta cita.'))

    meetup.status = PetMeetup.MeetupStatus.CANCELLED
    if reason:
        cancel_note = f' [Cancelado por tutor: {reason}]'
        meetup.notes = f'{meetup.notes}{cancel_note}'.strip()
    meetup.save(update_fields=['status', 'notes', 'updated_at'])
    return meetup


def complete_pet_meetup(meetup_id: int, user: Optional[Any] = None) -> PetMeetup:
    """
    Finaliza satisfactoriamente una cita de encuentro canino.
    Actualiza el estado a `COMPLETED`, lo que incrementa automáticamente
    el contador de encuentros completados en el perfil de ambos tutores
    (Profile.completed_meetings_count).
    """
    meetup = PetMeetup.objects.select_related(
        'host_pet', 'guest_pet', 'host_pet__owner', 'guest_pet__owner'
    ).get(id=meetup_id)

    if user:
        is_host_owner = meetup.host_pet.owner_id == user.id or meetup.host_pet.owner == user
        is_guest_owner = meetup.guest_pet.owner_id == user.id or meetup.guest_pet.owner == user
        is_staff = getattr(user, 'is_staff', False)
        if not (is_host_owner or is_guest_owner or is_staff):
            raise PermissionError(_('No tienes permiso para marcar como completada esta cita.'))

    meetup.status = PetMeetup.MeetupStatus.COMPLETED
    meetup.save(update_fields=['status', 'updated_at'])
    return meetup


# ==============================================================================
# Servicios de Gestión de Mascotas y Contexto de Vistas
# ==============================================================================


def serialize_pet_for_management(pet: Pet) -> dict[str, Any]:
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


def get_default_new_pet_data() -> dict[str, Any]:
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


def save_or_update_pet(user: Any, data: dict[str, Any], files: dict[str, Any]) -> tuple[Pet, bool]:
    """
    Guarda una nueva mascota o actualiza una existente perteneciente al tutor autenticado.
    Procesa atributos de especie, raza, fecha de nacimiento, color, temperamentos,
    objetivos en PetMatch, certificados y fotografía.
    Retorna la tupla (instancia_mascota, es_creada).
    """
    pet_name = str(data.get('name', 'Mascota')).strip()
    pet_id = str(data.get('pet_id', '')).strip()

    profile_color = data.get('profile_color', 'coral')
    species_slug = str(data.get('species', 'perro')).strip().lower()
    raw_gender = data.get('gender', 'M')
    gender = Pet.Gender.HEMBRA if raw_gender in ('H', 'hembra') else Pet.Gender.MACHO

    uploaded_photo = files.get('photo')
    remove_photo = str(data.get('remove_photo', '')).lower() == 'true'

    # Procesar fecha de nacimiento admitiendo distintos formatos habituales
    birth_date_val = None
    birth_date_str = str(data.get('birth_date', '')).strip()
    if birth_date_str:
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                birth_date_val = datetime.strptime(birth_date_str, fmt).date()
                break
            except ValueError:
                pass
    if not birth_date_val:
        birth_date_val = timezone.now().date()

    # Mapear el objetivo de cruza, socialización y adopción
    is_matching = data.get('is_matching') in ('true', 'on', '1', True)
    is_socializing = data.get('is_socializing') in ('true', 'on', '1', True)
    is_adoption = data.get('is_adoption') in ('true', 'on', '1', True)

    if is_matching and is_socializing:
        purpose_val = Pet.Purpose.BOTH
    elif is_matching and not is_socializing:
        purpose_val = Pet.Purpose.MATING
    elif not is_matching and is_socializing:
        purpose_val = Pet.Purpose.PLAY
    else:
        purpose_val = Pet.Purpose.MATING

    # Mapear el tipo de certificado
    raw_cert = str(data.get('certificate', '')).strip().lower()
    cert_map = {
        'fci': 'Certificado FCI',
        'tramite': 'En trámite',
        'sin_pedigri': 'Sin pedigrí',
    }
    cert_label = cert_map.get(raw_cert, 'Certificado FCI')

    # Obtener o registrar la especie asociada
    species_obj, _sp_created = PetSpecies.objects.get_or_create(
        slug=species_slug,
        defaults={'name': species_slug.capitalize(), 'icon_name': 'dog'},
    )

    # Buscar la mascota en base de datos si ya existe para este usuario
    db_pet = None
    if pet_id.isdigit():
        db_pet = Pet.objects.filter(id=int(pet_id), owner=user).first()
    if not db_pet:
        db_pet = Pet.objects.filter(name__iexact=pet_name, owner=user).first()

    is_created = False
    if db_pet:
        db_pet.name = pet_name
        db_pet.breed = data.get('breed', db_pet.breed)
        db_pet.species = species_obj
        db_pet.gender = gender
        db_pet.birth_date = birth_date_val
        db_pet.description = data.get('description', db_pet.description)
        db_pet.profile_color = profile_color
        db_pet.temperaments = data.get('temperaments', db_pet.temperaments)
        db_pet.is_active_for_match = is_matching
        db_pet.is_socializing = is_socializing
        db_pet.purpose = purpose_val
        db_pet.is_for_adoption = is_adoption
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
    else:
        db_pet = Pet.objects.create(
            owner=user,
            name=pet_name,
            species=species_obj,
            breed=data.get('breed', 'Mestizo'),
            gender=gender,
            birth_date=birth_date_val,
            profile_color=profile_color,
            description=data.get('description', ''),
            temperaments=data.get('temperaments', ''),
            is_active_for_match=is_matching,
            is_socializing=is_socializing,
            purpose=purpose_val,
            is_for_adoption=is_adoption,
            certificate_type=cert_label,
        )
        if uploaded_photo:
            db_pet.photo = uploaded_photo
            db_pet.save()
        is_created = True

    return db_pet, is_created


def update_pet_certificate(user: Any, pet_id: Any, certificate_val: str) -> tuple[Pet, str, str]:
    """
    Actualiza el certificado de pedigrí de una mascota perteneciente al usuario.
    Retorna la tupla (mascota, valor_certificado, etiqueta_certificado).
    """
    clean_val = certificate_val.strip().lower()
    cert_map = {
        'fci': _('Certificado FCI'),
        'tramite': _('En trámite'),
        'sin_pedigri': _('Sin pedigrí'),
    }
    cert_label = cert_map.get(clean_val, _('Certificado FCI'))

    pet = None
    if str(pet_id).isdigit():
        pet = Pet.objects.filter(id=int(pet_id), owner=user).first()
    if not pet:
        pet = Pet.objects.filter(name__iexact=str(pet_id), owner=user).first()

    if not pet:
        raise Pet.DoesNotExist(_('Mascota no encontrada o no pertenece al usuario actual.'))

    pet.certificate_type = cert_label
    if clean_val in ('sin_pedigri', 'tramite'):
        pet.certificate_number = ''
    pet.save(update_fields=['certificate_type', 'certificate_number', 'updated_at'])
    return pet, clean_val, cert_label


def toggle_pet_goal(user: Any, pet_id: Any, goal: str, is_enabled: bool) -> Pet:
    """
    Actualiza uno de los objetivos de la mascota (búsqueda de pareja, socialización, adopción).
    Recalcula automáticamente el propósito principal derivado.
    """
    pet = None
    if str(pet_id).isdigit():
        pet = Pet.objects.filter(id=int(pet_id), owner=user).first()
    if not pet:
        pet = Pet.objects.filter(name__iexact=str(pet_id), owner=user).first()

    if not pet:
        raise Pet.DoesNotExist(_('Mascota no encontrada o no pertenece al usuario actual.'))

    if goal == 'is_matching':
        pet.is_active_for_match = is_enabled
        if is_enabled:
            pet.purpose = Pet.Purpose.BOTH if pet.is_socializing else Pet.Purpose.MATING
        else:
            pet.purpose = Pet.Purpose.PLAY if pet.is_socializing else Pet.Purpose.MATING
    elif goal == 'is_socializing':
        pet.is_socializing = is_enabled
        if is_enabled:
            pet.purpose = Pet.Purpose.BOTH if pet.is_matching else Pet.Purpose.PLAY
        else:
            pet.purpose = Pet.Purpose.MATING
    elif goal == 'is_adoption':
        pet.is_for_adoption = is_enabled
    else:
        raise ValueError(_('Objetivo no válido.'))

    pet.save(
        update_fields=[
            'is_active_for_match',
            'is_socializing',
            'is_for_adoption',
            'purpose',
            'updated_at',
        ]
    )
    return pet


def delete_user_pet(user: Any, pet_id: Any) -> tuple[str, Optional[Pet]]:
    """
    Elimina una mascota de forma segura validando que pertenezca al usuario tutor.
    Retorna el nombre de la mascota eliminada y la siguiente mascota del usuario si existe.
    """
    pet = None
    if str(pet_id).isdigit():
        pet = Pet.objects.filter(id=int(pet_id), owner=user).first()
    if not pet:
        pet = Pet.objects.filter(name__iexact=str(pet_id), owner=user).first()

    if not pet:
        raise Pet.DoesNotExist(
            _('La mascota especificada no existe o no tienes permisos para eliminarla.')
        )

    pet_name = pet.name
    pet.delete()
    remaining_pet = Pet.objects.filter(owner=user).first()
    return pet_name, remaining_pet


def serialize_pet_for_select(pet: Pet, active_pet_id: str) -> dict[str, Any]:
    """Serializa una mascota para la tarjeta visual del selector interactivo."""
    has_fci = bool(pet.has_pedigree and pet.certificate == 'fci')
    interested_count = get_interested_match_requests(pet).count()
    return {
        'id': str(pet.id),
        'name': pet.name,
        'species': pet.species.slug if pet.species else 'perro',
        'species_label': str(pet.species_label),
        'gender': pet.gender,
        'gender_label': str(pet.gender_label),
        'gender_icon': pet.gender_icon,
        'is_hembra': pet.is_hembra,
        'breed': pet.breed,
        'age_text': str(pet.age_text),
        'photo_url': pet.photo_url,
        'is_active': pet.is_active_for_match,
        'is_matching': pet.is_active_for_match,
        'has_pedigree': pet.has_pedigree,
        'certificate': 'fci' if has_fci else pet.certificate,
        'certificate_label': str(pet.certificate_type or ''),
        'profile_color': pet.profile_color,
        'profile_color_hex': pet.profile_color_hex,
        'interested_count': interested_count,
        'is_selected': str(pet.id) == str(active_pet_id),
    }


def get_pet_select_context(
    user: Any,
    active_pet_obj: Pet,
    user_pets: list[Pet],
    pedigree_preference: str,
) -> dict[str, Any]:
    """Construye el contexto de datos para la pantalla de selección de mascota."""
    selected_id = str(active_pet_obj.id)
    pets_display = [serialize_pet_for_select(p, selected_id) for p in user_pets]
    active_pet_dict = next(
        (p for p in pets_display if p['id'] == selected_id),
        pets_display[0] if pets_display else {},
    )
    interested_count = active_pet_dict.get('interested_count', 0)

    clean_pedigree = (
        pedigree_preference
        if pedigree_preference in ('with_pedigree', 'without_pedigree', 'both')
        else 'both'
    )

    return {
        'pets': pets_display,
        'active_pet': active_pet_dict,
        'interested_count': interested_count,
        'pedigree_preference': clean_pedigree,
    }


def get_match_feed_context(
    active_pet: Pet,
    user_pets: list[Pet],
    session: Any,
    get_params: Any,
) -> dict[str, Any]:
    """
    Construye el contexto de datos para la pantalla del feed de descubrimiento y compatibilidad.
    Procesa filtros de recarga, pedigrí, distancia máxima y propósito de cruza.
    """
    other_pet = next((p for p in user_pets if p.id != active_pet.id), None)

    # Recarga del feed limpiando descartes previos si se solicita
    if get_params.get('reload') == 'true':
        MatchRequest.objects.filter(
            from_pet=active_pet,
            status=MatchRequest.RequestStatus.REJECTED,
        ).delete()
        session.pop('match_pedigree_preference', None)
        session.pop('match_max_distance', None)
        session.pop('match_purpose_preference', None)

    # Restablecimiento de filtros de búsqueda
    if get_params.get('reset_filters') == 'true':
        session.pop('match_pedigree_preference', None)
        session.pop('match_max_distance', None)
        session.pop('match_purpose_preference', None)

    # Preferencia de pedigrí
    pedigree_param = get_params.get('pedigree') or session.get('match_pedigree_preference', 'both')
    if pedigree_param not in ('with_pedigree', 'without_pedigree', 'both'):
        pedigree_param = 'both'
    session['match_pedigree_preference'] = pedigree_param

    # Distancia máxima permitida en kilómetros
    pet_default_dist = getattr(active_pet, 'max_search_distance_km', None) or 25
    raw_max_distance = get_params.get('max_distance')
    if raw_max_distance is not None:
        try:
            max_distance = int(float(raw_max_distance))
            if max_distance < 1:
                max_distance = 1
            elif max_distance > 50:
                max_distance = 50
            session['match_max_distance'] = max_distance
        except (ValueError, TypeError):
            max_distance = session.get('match_max_distance', pet_default_dist)
    else:
        max_distance = session.get('match_max_distance', pet_default_dist)

    # Propósito de cruza o socialización
    purpose_param = get_params.get('purpose') or session.get('match_purpose_preference', 'all')
    if purpose_param not in ('all', 'mating', 'play', 'both'):
        purpose_param = 'all'
    session['match_purpose_preference'] = purpose_param

    # Configurar filtros para la consulta ORM de candidatos
    match_filters = {'max_distance': max_distance}
    if pedigree_param == 'with_pedigree':
        match_filters['has_pedigree'] = True
    elif pedigree_param == 'without_pedigree':
        match_filters['without_pedigree'] = True
    if purpose_param != 'all':
        match_filters['purpose'] = purpose_param

    # Consultar y serializar candidatos compatibles
    candidates_qs = get_match_candidates(active_pet, filters=match_filters)
    candidates_data = [serialize_candidate(active_pet, c) for c in candidates_qs]
    current_candidate = candidates_data[0] if candidates_data else None

    # Contadores de solicitudes asociadas a la mascota activa
    tab_counters = get_requests_tab_counters(active_pet)
    total_requests_count = tab_counters['all']
    interested_count = tab_counters['interested']
    pending_interested_count = tab_counters['pending']

    # Consultar solicitudes entrantes pendientes para la barra lateral
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

    return {
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


def get_match_interested_context(
    active_pet: Pet,
    user_pets: list[Pet],
    tab: str = 'all',
    sort_by: str = 'compatibility',
) -> dict[str, Any]:
    """
    Construye el contexto de datos para la bandeja de interesados y solicitudes de emparejamiento.
    Filtra por pestaña, ordena candidatos y obtiene los encuentros próximos.
    """
    other_pet = next((p for p in user_pets if p.id != active_pet.id), None)

    # Obtener contadores para las pestañas de navegación
    tab_counters = get_requests_tab_counters(active_pet)

    # Filtrar solicitudes según la pestaña seleccionada
    clean_tab = tab.strip().lower()
    if clean_tab == 'interested':
        requests_qs = get_interested_match_requests(active_pet)
    elif clean_tab == 'sent':
        requests_qs = get_sent_match_requests(active_pet)
    elif clean_tab == 'matches':
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
        clean_tab = 'all'
        requests_qs = get_all_match_requests_for_pet(active_pet)

    suitors = [serialize_match_request(active_pet, r) for r in requests_qs] if active_pet else []

    # Ordenar pretendientes según el criterio elegido
    clean_sort = sort_by.strip().lower()
    if clean_sort not in ['compatibility', 'distance', 'recent']:
        clean_sort = 'compatibility'

    if suitors:
        if clean_sort == 'compatibility':
            suitors.sort(
                key=lambda s: (s.get('compatibility_val', 0), s.get('created_timestamp', 0)),
                reverse=True,
            )
        elif clean_sort == 'distance':
            suitors.sort(
                key=lambda s: (s.get('distance_val', 999.0), -s.get('created_timestamp', 0))
            )
        elif clean_sort == 'recent':
            suitors.sort(key=lambda s: s.get('created_timestamp', 0), reverse=True)

    # Obtener encuentros confirmados y propuestos para la agenda
    meetups_qs = get_upcoming_pet_meetups(active_pet) if active_pet else []
    confirmed_dates = [serialize_pet_meetup(active_pet, m) for m in meetups_qs]

    return {
        'active_pet': active_pet,
        'other_pet': other_pet,
        'suitors': suitors,
        'requests': suitors,
        'featured_suitor': suitors[0] if suitors else None,
        'secondary_suitors': suitors[1:] if len(suitors) > 1 else [],
        'interested_count': tab_counters.get('interested', 0),
        'tab_counters': tab_counters,
        'current_tab': clean_tab,
        'current_sort': clean_sort,
        'confirmed_dates': confirmed_dates,
    }
