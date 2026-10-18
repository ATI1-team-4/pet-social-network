from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.core.models import AuditLog
from apps.core.services import log_audit_event

User = get_user_model()


class AuditServiceTests(TestCase):
    """Pruebas unitarias para el servicio transversal de auditoría."""

    def test_log_audit_event_authenticated_user(self):
        """Registra un evento asociando correctamente al usuario autenticado."""
        # Obtenemos al desarrollador Edwyn Guzmán
        user = User.objects.get(username='edwyn')

        # Registrar el evento en el servicio
        log = log_audit_event(
            action='Inicio de sesión exitoso',
            user=user,
            ip_address='10.0.0.1',
            details='El usuario inició sesión en el sistema',
        )

        # Comprobamos que el objeto retornado sea una instancia del modelo AuditLog
        self.assertIsInstance(log, AuditLog)
        # Verificamos que los campos se hayan persistido con los valores correctos
        self.assertEqual(log.user, user)
        self.assertEqual(log.action, 'Inicio de sesión exitoso')
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_log_audit_event_anonymous_user(self):
        """Permite registrar eventos anónimos dejando el campo de usuario como nulo."""
        # Registrar un evento con AnonymousUser
        log = log_audit_event(
            action='Intento de acceso fallido',
            user=AnonymousUser(),
            ip_address='10.0.0.2',
            details='Credenciales inválidas',
        )

        # Comprobamos que sea una instancia de AuditLog
        self.assertIsInstance(log, AuditLog)
        # Verificamos que el usuario quede en None (nulo) para acciones anónimas
        self.assertIsNone(log.user)
        self.assertEqual(log.action, 'Intento de acceso fallido')
