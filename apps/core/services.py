"""Servicios transversales y utilidades del núcleo del sistema."""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.core.models import AuditLog

User = get_user_model()


def log_audit_event(
    *,
    action: str,
    user: Any = None,
    ip_address: str | None = None,
    details: str = '',
) -> AuditLog:
    """
    Registra un evento en la tabla de auditoría del sistema.

    Maneja usuarios anónimos o no autenticados asignando None al campo user.
    """
    user_instance = (
        user
        if user and not isinstance(user, AnonymousUser) and getattr(user, 'is_authenticated', False)
        else None
    )
    return AuditLog.objects.create(
        user=user_instance,
        action=action,
        ip_address=ip_address,
        details=details,
    )
