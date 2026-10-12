"""
Capa de servicios y lógica de negocio para la aplicación pets.

Define las siluetas de las funciones especializadas para:
- Descubrimiento y evaluación de candidatos en el feed de emparejamiento (#63).
- Gestión de solicitudes e interesados en el emparejamiento (#64).
- Concertación de citas y agenda de encuentros seguros (#65).
"""

from datetime import date, time
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.accounts.models import UserReport
from apps.pets.models import MatchRequest, Pet, PetMeetup

User = get_user_model()


def get_user_pets(user_id: Any) -> list[Any]:
    """Obtiene el listado de mascotas pertenecientes a un tutor."""
    return list(Pet.objects.filter(owner_id=user_id).order_by('id'))


# ==============================================================================
# Siluetas de Servicio para Feed y Descubrimiento de Candidatos (Issue #63)
# ==============================================================================


def get_match_candidates(
    active_pet: Pet, filters: Optional[dict[str, Any]] = None
) -> QuerySet[Pet]:
    """
    Silueta: Consulta en base de datos los candidatos compatibles para el feed.

    Requerimientos del equipo:
    - Filtrar por sexo opuesto (`gender != active_pet.gender`).
    - Excluir a la propia mascota activa (`id != active_pet.id`).
    - Excluir mascotas pertenecientes al mismo tutor (`owner != active_pet.owner`).
    - Excluir candidatos ya evaluados (likes previos o descartes registrados en MatchRequest).
    - Considerar estado `is_active_for_match = True`.
    - Aplicar filtros opcionales de distancia máxima, certificados y especie/raza.
    """
    raise NotImplementedError('El equipo debe implementar el filtrado de candidatos en el feed.')


def record_candidate_like(active_pet: Pet, candidate_pet: Pet) -> tuple[MatchRequest, bool]:
    """
    Silueta: Registra el interés ('Me gusta') hacia un candidato y detecta match mutuo.

    Requerimientos del equipo:
    - Crear o actualizar registro en `MatchRequest` con `from_pet=active_pet` y `to_pet=candidate_pet`.
    - Verificar si ya existía una solicitud previa de `candidate_pet` hacia `active_pet`.
    - Si existe reciprocidad, actualizar el estado a `MatchRequest.RequestStatus.ACCEPTED`
      y retornar `(match_request, is_mutual=True)`.
    - En caso contrario, registrar con estado `PENDING` y retornar `(match_request, is_mutual=False)`.
    """
    raise NotImplementedError(
        'El equipo debe implementar el registro de likes y detección de reciprocidad.'
    )


def record_candidate_pass(active_pet: Pet, candidate_pet: Pet) -> MatchRequest:
    """
    Silueta: Registra el descarte de un candidato para evitar volver a mostrarlo en el feed.

    Requerimientos del equipo:
    - Crear o actualizar registro en `MatchRequest` con estado `REJECTED`
      o registrar en un historial de candidatos descartados según la regla de negocio.
    """
    raise NotImplementedError('El equipo debe implementar el registro de descarte de candidatos.')


def report_candidate_pet(
    reporter_user: Any,
    reported_pet: Pet,
    reason: str,
    admin_notes: str = '',
) -> UserReport:
    """
    Silueta: Registra una denuncia o reporte contra una mascota o su tutor desde el feed.

    Requerimientos del equipo:
    - Crear instancia en `UserReport` asociando `reported_by=reporter_user`,
      `reported_pet=reported_pet`, `reported_user=reported_pet.owner`, `reason=reason`.
    """
    raise NotImplementedError('El equipo debe implementar el registro de reportes de candidatos.')


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
