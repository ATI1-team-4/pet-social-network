"""
Señales de autenticación y seguridad para el módulo accounts.
Conecta eventos de acceso del sistema con AuditLog en apps/core/models.py.
"""

from typing import Any

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from apps.core.services import log_audit_event


def get_client_ip(request: Any) -> str | None:
    """Extrae la dirección IP del cliente a partir de la petición HTTP."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Registra en auditoría el inicio de sesión exitoso de un usuario."""
    ip = get_client_ip(request)
    log_audit_event(
        action='LOGIN_SUCCESS',
        user=user,
        ip_address=ip,
        details=f'Inicio de sesión exitoso para el usuario {user.username}',
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Registra en auditoría el cierre de sesión de un usuario."""
    ip = get_client_ip(request)
    username = user.username if user else 'anónimo'
    log_audit_event(
        action='LOGOUT',
        user=user,
        ip_address=ip,
        details=f'Cierre de sesión para el usuario {username}',
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Registra en auditoría los intentos fallidos de inicio de sesión."""
    ip = get_client_ip(request)
    attempted_identity = credentials.get('username') or credentials.get('email') or 'no provisto'
    log_audit_event(
        action='LOGIN_FAILED',
        user=None,
        ip_address=ip,
        details=f'Intento fallido de inicio de sesión con identificador: {attempted_identity}',
    )
