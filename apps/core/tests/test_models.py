from django.db import models
from django.test import TestCase

from apps.core.models import TimeStampedModel


class ConcreteTimeStampedModel(TimeStampedModel):
    """Modelo concreto auxiliar para comprobar la herencia del modelo abstracto."""

    name = models.CharField(max_length=50)

    class Meta:
        app_label = 'core'


class TimeStampedModelTests(TestCase):
    """Pruebas para el modelo base abstracto TimeStampedModel."""

    def test_timestamped_model_is_abstract(self):
        """Verifica que TimeStampedModel esté configurado como modelo abstracto."""
        # Comprobamos que la clase esté definida con abstract=True en sus metadatos de Django
        self.assertTrue(TimeStampedModel._meta.abstract)

    def test_concrete_model_inherits_timestamp_fields(self):
        """Verifica que el modelo concreto herede los campos created_at y updated_at."""
        # Verificamos que ambos campos de fecha existan en el modelo hijo concreto
        fields = [f.name for f in ConcreteTimeStampedModel._meta.get_fields()]
        self.assertIn('created_at', fields)
        self.assertIn('updated_at', fields)

        # Comprobamos que auto_now_add y auto_now estén activos en cada campo
        created_at_field = ConcreteTimeStampedModel._meta.get_field('created_at')
        updated_at_field = ConcreteTimeStampedModel._meta.get_field('updated_at')
        self.assertTrue(created_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)


class AuditLogModelTests(TestCase):
    """Pruebas unitarias para el modelo AuditLog."""

    def test_create_audit_log_anonymous(self):
        """Verifica la creación de un registro de auditoría sin usuario autenticado."""
        from apps.core.models import AuditLog

        # Creamos un evento de prueba sin usuario asociado
        log = AuditLog.objects.create(
            action='Acción anónima',
            ip_address='192.168.1.1',
            details='Detalles de prueba',
        )

        # Comprobamos que el registro tenga clave primaria (pk) y marcas de tiempo
        self.assertIsNotNone(log.pk)
        self.assertIn('Anónimo', str(log))
        self.assertIn('Acción anónima', str(log))
        self.assertIsNotNone(log.created_at)
        self.assertIsNotNone(log.updated_at)
