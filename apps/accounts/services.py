"""Capa de servicios y lógica de negocio para el módulo accounts."""

from typing import Any, Optional

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import UserProfile
from apps.core.services import log_audit_event
from apps.pets.models import MatchRequest

User = get_user_model()


def authenticate_by_email_or_username(
    request: Any,
    identifier: str,
    password: str,
) -> Any:
    """
    Autentica un usuario verificando su identificador contra email o username.
    Soporta mayúsculas y minúsculas indistintamente en el correo.
    """
    identifier_clean = identifier.strip()
    user_match = (
        User.objects.filter(email__iexact=identifier_clean).first()
        or User.objects.filter(username__iexact=identifier_clean).first()
    )

    if user_match:
        return authenticate(request, username=user_match.username, password=password)

    # Si no coincide con ninguno, intentamos autenticar directamente para emitir la señal user_login_failed
    return authenticate(request, username=identifier_clean, password=password)


@transaction.atomic
def create_tutor_user(
    *,
    full_name: str,
    email: str,
    password: str,
    phone_prefix: str = '+58',
    phone: str = '',
    id_type: str = 'V',
    id_number: str = '',
    ip_address: str | None = None,
) -> Any:
    """
    Crea una cuenta de usuario con el rol Tutor y su perfil asociado.
    Garantiza atomicidad y registro en el historial de auditoría.
    """
    email_clean = email.strip().lower()
    name_parts = full_name.strip().split()
    first_name = name_parts[0] if name_parts else ''
    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

    # Base para el nombre de usuario único a partir del correo
    base_username = email_clean.split('@')[0][:120]
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base_username}_{counter}'
        counter += 1

    # Crear el usuario en Django auth
    user = User.objects.create_user(
        username=username,
        email=email_clean,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    # Asignar automáticamente el rol de Tutor
    tutor_group, _tutor_group_created = Group.objects.get_or_create(name='Tutor')
    user.groups.add(tutor_group)

    # Crear el perfil con los datos complementarios de tutor
    UserProfile.objects.create(
        user=user,
        phone_prefix=phone_prefix.strip(),
        phone_number=phone.strip(),
        id_type=id_type.strip().upper(),
        id_number=id_number.strip(),
    )

    # Registrar evento de creación en AuditLog
    log_audit_event(
        action='REGISTER_SUCCESS',
        user=user,
        ip_address=ip_address,
        details=f'Registro de nuevo tutor: {user.username} ({email_clean}) con cédula {id_type}-{id_number}',
    )

    return user


def get_user_profile_context(user: Any, session_active_pet_id: Optional[str] = None) -> dict[str, Any]:
    """
    Construye el contexto de datos para la pantalla de perfil del tutor autenticado.
    Obtiene las mascotas registradas, calcula conexiones de match y resuelve la mascota activa.
    """
    # Consultar las mascotas registradas por el usuario actual
    user_pets = user.pets.select_related('species').all()
    pets_count = user_pets.count()

    # Contabilizar solicitudes de match aceptadas donde intervenga alguna mascota del tutor
    active_connections_count = MatchRequest.objects.filter(
        Q(from_pet__in=user_pets) | Q(to_pet__in=user_pets),
        status=MatchRequest.RequestStatus.ACCEPTED,
    ).count()

    # Localizar la mascota activa preferida o asignar la primera disponible
    active_pet = None
    if session_active_pet_id and str(session_active_pet_id).isdigit():
        active_pet = user_pets.filter(id=int(session_active_pet_id)).first()

    if not active_pet:
        active_pet = user_pets.filter(is_active_for_match=True).first() or user_pets.first()

    return {
        'user_pets': user_pets,
        'pets_count': pets_count,
        'active_connections_count': active_connections_count,
        'active_pet': active_pet,
    }


@transaction.atomic
def update_user_profile(user: Any, data: dict[str, Any], files: dict[str, Any]) -> tuple[Any, UserProfile]:
    """
    Actualiza la información personal, ubicación, preferencias y avatar del tutor autenticado.
    Garantiza consistencia transaccional y persistencia de medios.
    """
    # Obtener o crear el perfil del usuario autenticado
    profile, _profile_created = UserProfile.objects.get_or_create(user=user)

    # Actualizar nombres y apellidos si se suministraron
    full_name = str(data.get('full_name', '')).strip()
    user_dirty = False
    if full_name:
        parts = full_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user_dirty = True

    # Actualizar correo electrónico
    email = str(data.get('email', '')).strip()
    if email:
        user.email = email
        user_dirty = True

    if user_dirty:
        user.save(update_fields=['first_name', 'last_name', 'email'])

    # Actualizar datos de contacto y localización
    profile.phone_number = str(data.get('phone', profile.phone_number)).strip()
    profile.state = str(data.get('state', profile.state)).strip()
    profile.municipality = str(data.get('municipality', profile.municipality)).strip()
    profile.neighborhood = str(data.get('neighborhood', profile.neighborhood)).strip()
    if 'city' in data and not data.get('municipality'):
        profile.municipality = str(data.get('city', '')).strip()

    # Procesar coordenadas de latitud
    if 'latitude' in data:
        lat_val = str(data.get('latitude', '')).strip()
        if lat_val:
            try:
                profile.latitude = float(lat_val)
            except ValueError:
                pass
        else:
            profile.latitude = None

    # Procesar coordenadas de longitud
    if 'longitude' in data:
        lon_val = str(data.get('longitude', '')).strip()
        if lon_val:
            try:
                profile.longitude = float(lon_val)
            except ValueError:
                pass
        else:
            profile.longitude = None

    # Procesar fecha de nacimiento
    birth_date_val = str(data.get('birth_date', '')).strip()
    if birth_date_val:
        try:
            profile.birth_date = birth_date_val
        except (ValueError, TypeError):
            pass

    # Procesar sexo del tutor
    gender_val = str(data.get('gender', '')).strip()
    if gender_val:
        profile.gender = (
            'F'
            if gender_val in ('Femenino', 'F', 'f')
            else ('M' if gender_val in ('Masculino', 'M', 'm') else 'O')
        )

    # Actualizar gustos y pasatiempos
    profile.favorite_color = str(data.get('favorite_color', profile.favorite_color)).strip()
    profile.favorite_book = str(data.get('favorite_book', profile.favorite_book)).strip()
    profile.favorite_music = str(data.get('favorite_music', profile.favorite_music)).strip()
    profile.favorite_videogame = str(
        data.get('favorite_game', profile.favorite_videogame)
    ).strip()

    # Procesar eliminación del avatar actual
    if str(data.get('remove_avatar', '')).lower() == 'true' and profile.avatar:
        profile.avatar.delete(save=False)
        profile.avatar = None

    # Procesar subida de nueva fotografía de avatar
    if 'avatar' in files:
        profile.avatar = files['avatar']

    profile.save()
    return user, profile
