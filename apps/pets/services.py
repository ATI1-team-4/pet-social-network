"""
Capa de servicios y lógica de negocio para la aplicación pets.

Define las siluetas de las funciones especializadas para:
- Descubrimiento y evaluación de candidatos en el feed de emparejamiento (#63).
- Gestión de solicitudes e interesados en el emparejamiento (#64).
- Concertación de citas y agenda de encuentros seguros (#65).
"""

import math
from datetime import date, time
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
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


def calculate_candidate_distance(active_pet: Pet, candidate_pet: Pet) -> str:
    """
    Calcula una distancia aproximada entre los tutores de ambas mascotas.
    Si ambos perfiles cuentan con coordenadas geográficas (lat/lon), utiliza la fórmula de Haversine.
    En caso contrario, estima según similitud de municipio/estado o proporciona un estimado amigable.
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
        lat1, lon1 = p1.latitude, p1.longitude
        lat2, lon2 = p2.latitude, p2.longitude
        radius = 6371.0  # Radio terrestre en km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
        km = round(radius * c, 1)
        return f'A {km} km' if km >= 0.5 else 'A menos de 1 km'

    if p1 and p2 and p1.municipality and p2.municipality:
        if p1.municipality.lower() == p2.municipality.lower():
            return 'A 1.5 km'
        if p1.state and p2.state and p1.state.lower() == p2.state.lower():
            return 'A 4.2 km'

    return 'A 2.5 km'


def calculate_candidate_compatibility(active_pet: Pet, candidate_pet: Pet) -> int:
    """
    Calcula el porcentaje de afinidad biológica y conductual (70% - 99%).
    Evalúa compatibilidad de raza, propósito de emparejamiento, certificación y temperamento.
    """
    score = 80

    # Misma raza incrementa afinidad notablemente
    if (
        active_pet.breed
        and candidate_pet.breed
        and active_pet.breed.strip().lower() == candidate_pet.breed.strip().lower()
    ):
        score += 12
    else:
        score += 4

    # Coincidencia de propósitos (ambos cruza o socialización)
    if (
        active_pet.purpose == candidate_pet.purpose
        or active_pet.purpose == Pet.Purpose.BOTH
        or candidate_pet.purpose == Pet.Purpose.BOTH
    ):
        score += 4

    # Pedigrí o certificado FCI verificado
    if active_pet.has_pedigree and candidate_pet.has_pedigree:
        score += 3

    # Temperamentos compartidos
    t1 = set(active_pet.temperament_list)
    t2 = set(candidate_pet.temperament_list)
    common = len(t1.intersection(t2))
    score += min(common * 2, 6)

    return min(max(score, 72), 99)


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
    cert_str = (
        candidate_pet.certificate_number or candidate_pet.certificate_type or 'Certificado FCI'
    )

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
        'certificate_label': str(candidate_pet.certificate_type or 'Certificado FCI'),
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
                Q(certificate_number__isnull=False) & ~Q(certificate_number='')
                | Q(certificate_type__icontains='fci')
            )
        if filters.get('purpose'):
            queryset = queryset.filter(purpose=filters['purpose'])

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


def get_interested_match_requests(active_pet: Pet) -> QuerySet[MatchRequest]:
    """
    Silueta: Obtiene las solicitudes de match recibidas hacia la mascota activa (Interesados).

    Requerimientos del equipo:
    - Consultar `MatchRequest.objects.filter(to_pet=active_pet)`.
    - Permitir filtrado por estados (`pending`, `accepted`, `rejected`).
    - Optimizar consultas con `select_related('from_pet', 'from_pet__owner')`.
    """
    raise NotImplementedError('El equipo debe implementar la consulta de solicitudes recibidas.')


def get_sent_match_requests(active_pet: Pet) -> QuerySet[MatchRequest]:
    """
    Silueta: Obtiene las solicitudes de match enviadas por la mascota activa.

    Requerimientos del equipo:
    - Consultar `MatchRequest.objects.filter(from_pet=active_pet)`.
    - Optimizar consultas con `select_related('to_pet', 'to_pet__owner')`.
    """
    raise NotImplementedError('El equipo debe implementar la consulta de solicitudes enviadas.')


def get_requests_tab_counters(active_pet: Pet) -> dict[str, int]:
    """
    Silueta: Calcula dinámicamente los contadores de solicitudes para las pestañas.

    Requerimientos del equipo:
    - Retornar diccionario: {'all': total, 'interested': pendientes_recibidas, 'sent': enviadas}.
    """
    raise NotImplementedError('El equipo debe implementar el cálculo de contadores por pestaña.')


def accept_match_request(request_id: int, active_pet: Pet) -> MatchRequest:
    """
    Silueta: Acepta una solicitud de match recibida.

    Requerimientos del equipo:
    - Validar que la solicitud pertenezca a `to_pet == active_pet`.
    - Actualizar estado a `MatchRequest.RequestStatus.ACCEPTED`.
    - Retornar la instancia actualizada.
    """
    raise NotImplementedError('El equipo debe implementar la aceptación de solicitudes de match.')


def reject_match_request(request_id: int, active_pet: Pet) -> MatchRequest:
    """
    Silueta: Rechaza o descarta una solicitud de match recibida.

    Requerimientos del equipo:
    - Validar que la solicitud pertenezca a `to_pet == active_pet`.
    - Actualizar estado a `MatchRequest.RequestStatus.REJECTED`.
    - Retornar la instancia actualizada.
    """
    raise NotImplementedError('El equipo debe implementar el rechazo de solicitudes de match.')


def send_initial_match_note(
    request_id: int,
    sender_user: Any,
    note_text: str,
) -> dict[str, Any]:
    """
    Silueta: Registra o actualiza la nota de contacto asociada a la solicitud en `MatchRequest.notes`.

    Requerimientos del equipo:
    - Validar que la solicitud esté asociada a las mascotas involucradas.
    - Persistir la nota en el campo `notes` del modelo `MatchRequest`.
    """
    raise NotImplementedError(
        'El equipo debe implementar el guardado de la nota de solicitud en MatchRequest.'
    )


# ==============================================================================
# Siluetas de Servicio para Encuentros y Citas Seguras (Issue #65)
# ==============================================================================


def get_upcoming_pet_meetups(active_pet: Pet) -> QuerySet[PetMeetup]:
    """
    Silueta: Obtiene las citas confirmadas o pendientes próximas para la barra lateral.

    Requerimientos del equipo:
    - Consultar `PetMeetup` donde `requester_pet == active_pet` o `target_pet == active_pet`.
    - Filtrar por fecha futura o de hoy (`meeting_date >= date.today()`).
    - Ordenar cronológicamente por `meeting_date`, `meeting_time`.
    """
    raise NotImplementedError('El equipo debe implementar la consulta de citas programadas.')


def schedule_pet_meetup(
    requester_user: Any,
    requester_pet: Pet,
    target_pet: Pet,
    meeting_date: date,
    meeting_time: time,
    location_name: str,
    location_address: str = '',
    notes: str = '',
) -> PetMeetup:
    """
    Silueta: Persiste la concertación de una nueva cita de socialización o cruza responsable.

    Requerimientos del equipo:
    - Validar que `requester_pet.owner == requester_user`.
    - Validar que la fecha y hora sean futuras.
    - Crear instancia en `PetMeetup` con estado `SCHEDULED`.
    """
    raise NotImplementedError('El equipo debe implementar la concertación de citas en PetMeetup.')


def cancel_pet_meetup(meetup_id: int, user: Any, reason: str = '') -> PetMeetup:
    """
    Silueta: Cancela una cita de encuentro previamente acordada.

    Requerimientos del equipo:
    - Validar que el usuario sea dueño de `requester_pet` o de `target_pet`.
    - Actualizar estado de `PetMeetup` a `CANCELLED`.
    - Retornar la instancia cancelada.
    """
    raise NotImplementedError('El equipo debe implementar la cancelación de encuentros caninos.')
