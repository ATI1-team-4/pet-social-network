"""
Capa de servicios y lógica de negocio para la aplicación pets.

Define las siluetas de las funciones especializadas para:
- Descubrimiento y evaluación de candidatos en el feed de emparejamiento (#63).
- Gestión de solicitudes e interesados en el emparejamiento (#64).
- Concertación de citas y agenda de encuentros seguros (#65).
"""

import math
from datetime import date, datetime, time
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import UserReport
from apps.pets.models import MatchRequest, Pet, PetMeetup

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
    return f'A {km} km'


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
    # 1. Especie: Deben pertenecer a la misma especie
    same_species = False
    if getattr(active_pet, 'species_id', None) and getattr(candidate_pet, 'species_id', None):
        same_species = active_pet.species_id == candidate_pet.species_id
    elif getattr(active_pet, 'species', None) and getattr(candidate_pet, 'species', None):
        s1 = getattr(active_pet.species, 'slug', None) or str(active_pet.species).lower()
        s2 = getattr(candidate_pet.species, 'slug', None) or str(candidate_pet.species).lower()
        same_species = s1 == s2

    if not same_species:
        return 0

    # 2. Sexo: Compatibilidad biológica (opuesto vs mismo sexo)
    is_opposite_sex = (
        (active_pet.is_macho and candidate_pet.is_hembra)
        or (active_pet.is_hembra and candidate_pet.is_macho)
        or (active_pet.gender != candidate_pet.gender)
    )

    # 3. Raza: Coincidencia exacta de raza
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
    tutor_reviews = '12 citas'
    if owner_profile:
        tutor_rating = str(owner_profile.rating)
        meetings = owner_profile.completed_meetings_count
        tutor_reviews = f'{meetings} citas' if meetings > 0 else '5 citas'

    birth_str = (
        candidate_pet.birth_date.strftime('%d / %b / %Y')
        if candidate_pet.birth_date
        else 'No especificada'
    )
    weight_str = f'{candidate_pet.weight_kg} kg' if candidate_pet.weight_kg else 'No especificado'
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
        'temperaments': candidate_pet.temperament_list or ['Sociable', 'Juguetón'],
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
            queryset = queryset.filter(
                (
                    (
                        Q(certificate_number__isnull=False)
                        & ~Q(certificate_number='')
                        & ~Q(certificate_number__icontains='sin')
                    )
                    | Q(certificate_type__icontains='fci')
                    | Q(certificate_type__icontains='pedigr')
                    | Q(certificate_type__icontains='pedigree')
                )
                & ~Q(certificate_type__icontains='sin')
                & ~Q(certificate_type__icontains='tramite')
                & ~Q(certificate_type__icontains='trámite')
            )
        elif filters.get('without_pedigree'):
            queryset = queryset.filter(
                Q(certificate_type__icontains='sin')
                | Q(certificate_type__icontains='tramite')
                | Q(certificate_type__icontains='trámite')
                | (
                    (
                        Q(certificate_number__isnull=True)
                        | Q(certificate_number='')
                        | Q(certificate_number__icontains='sin')
                    )
                    & ~Q(certificate_type__icontains='fci')
                    & ~Q(certificate_type__icontains='pedigr')
                    & ~Q(certificate_type__icontains='pedigree')
                )
            )
        if filters.get('purpose'):
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
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(to_pet=active_pet)
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
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(from_pet=active_pet)
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
    """
    if not active_pet or not getattr(active_pet, 'id', None):
        return MatchRequest.objects.none()

    qs = (
        MatchRequest.objects.filter(Q(to_pet=active_pet) | Q(from_pet=active_pet))
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
    all_count = all_qs.count()

    return {
        'all': all_count,
        'interested': interested_count,
        'sent': sent_count,
        'pending': pending_count,
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
    Rechaza o descarta una solicitud de match en la bandeja.
    Valida que pertenezca a la mascota activa (como destinataria o remitente) y actualiza a REJECTED.
    """
    match_request = MatchRequest.objects.select_related('from_pet', 'to_pet').get(
        Q(to_pet=active_pet) | Q(from_pet=active_pet),
        id=request_id,
    )
    match_request.status = MatchRequest.RequestStatus.REJECTED
    match_request.save(update_fields=['status', 'updated_at'])
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
    tutor_signature = f'{tutor_full_name} ({_("Tutor de")} {candidate.name})'

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
        'certificate': candidate.certificate_type
        or (_('Certificado FCI') if candidate.has_pedigree else ''),
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
        'temperaments': candidate.temperament_list or [_('Sociable'), _('Juguetón')],
        'quote': req.notes
        or candidate.description
        or _('Interesado en conectar y evaluar compatibilidad.'),
        'tutor_name': tutor_full_name,
        'tutor_signature': tutor_signature,
        'status': req.status,
        'status_label': req.get_status_display(),
        'is_received': is_received,
        'is_sent': not is_received,
        'type': 'interested' if is_received else 'sent',
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
        PetMeetup.objects.filter(Q(pet1=active_pet) | Q(pet2=active_pet))
        .filter(
            date__gte=date.today(),
            status__in=[PetMeetup.MeetupStatus.CONFIRMED, PetMeetup.MeetupStatus.PROPOSED],
        )
        .select_related('pet1', 'pet2', 'pet1__owner', 'pet2__owner')
        .order_by('date', 'time')
    )


def serialize_pet_meetup(active_pet: Pet, meetup: PetMeetup) -> dict[str, Any]:
    """
    Serializa un encuentro de PetMeetup para su renderizado en la barra lateral de citas confirmadas.
    """
    other_pet = meetup.pet2 if meetup.pet1_id == active_pet.id else meetup.pet1
    time_str = meetup.time.strftime('%I:%M %p') if meetup.time else ''
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

    if requester_pet.id == target_pet.id:
        raise ValueError(_('No se puede programar un encuentro de una mascota consigo misma.'))

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
  
    active_statuses = [
        PetMeetup.MeetupStatus.CONFIRMED,
        PetMeetup.MeetupStatus.PROPOSED,
    ]

    has_conflict = PetMeetup.objects.filter(
        Q(pet1__in=[requester_pet, target_pet])
        | Q(pet2__in=[requester_pet, target_pet]),
        status__in=active_statuses,
    ).exists()

    if has_conflict:
        raise ValueError(
            _('Una de las mascotas ya tiene un encuentro agendado.')
        )


    if has_conflict:
        raise ValueError(
            _(
                'Una de las mascotas ya tiene una cita activa. '
                'Cancela o completa la cita existente antes de agendar otra.'
            )
        )

    # Vincular MatchRequest correspondiente si existe
    match_req = MatchRequest.objects.filter(
        Q(from_pet=requester_pet, to_pet=target_pet) | Q(from_pet=target_pet, to_pet=requester_pet)
    ).first()

    meetup = PetMeetup.objects.create(
        match_request=match_req,
        pet1=requester_pet,
        pet2=target_pet,
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
    - Validar que el usuario sea tutor de `pet1` o de `pet2` (o staff).
    - Actualizar estado de `PetMeetup` a `CANCELLED`.
    - Retornar la instancia cancelada.
    """
    meetup = PetMeetup.objects.select_related(
        'pet1', 'pet2', 'pet1__owner', 'pet2__owner'
    ).get(id=meetup_id)

    is_pet1_owner = meetup.pet1.owner_id == user.id or meetup.pet1.owner == user
    is_pet2_owner = meetup.pet2.owner_id == user.id or meetup.pet2.owner == user
    is_staff = getattr(user, 'is_staff', False)

    if not (is_pet1_owner or is_pet2_owner or is_staff):
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
        'pet1', 'pet2', 'pet1__owner', 'pet2__owner'
    ).get(id=meetup_id)

    if user:
        is_pet1_owner = meetup.pet1.owner_id == user.id or meetup.pet1.owner == user
        is_pet2_owner = meetup.pet2.owner_id == user.id or meetup.pet2.owner == user
        is_staff = getattr(user, 'is_staff', False)
        if not (is_pet1_owner or is_pet2_owner or is_staff):
            raise PermissionError(
                _('No tienes permiso para marcar como completada esta cita.')
            )

    meetup.status = PetMeetup.MeetupStatus.COMPLETED
    meetup.save(update_fields=['status', 'updated_at'])
    return meetup
