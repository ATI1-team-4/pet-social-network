from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.core.models import AuditLog
from apps.core.services import log_audit_event

User = get_user_model()


class AuditServiceTests(TestCase):
    """Pruebas unitarias para el servicio transversal de auditoría."""

    def test_log_audit_event_authenticated_user(self):
        user = User.objects.create_user(username='audituser', password='password123')
        log = log_audit_event(
            action='Inicio de sesión exitoso',
            user=user,
            ip_address='10.0.0.1',
            details='El usuario inició sesión en el sistema',
        )
        self.assertIsInstance(log, AuditLog)
        self.assertEqual(log.user, user)
        self.assertEqual(log.action, 'Inicio de sesión exitoso')
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_log_audit_event_anonymous_user(self):
        log = log_audit_event(
            action='Intento de acceso fallido',
            user=AnonymousUser(),
            ip_address='10.0.0.2',
            details='Credenciales inválidas',
        )
        self.assertIsInstance(log, AuditLog)
        self.assertIsNone(log.user)
        self.assertEqual(log.action, 'Intento de acceso fallido')
