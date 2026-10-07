"""Capa de servicios y lógica de negocio para el módulo accounts."""

from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from apps.accounts.models import UserProfile
from apps.core.services import log_audit_event

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
    tutor_group, _ = Group.objects.get_or_create(name='Tutor')
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
