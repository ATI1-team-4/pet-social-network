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
        self.assertTrue(TimeStampedModel._meta.abstract)

    def test_concrete_model_inherits_timestamp_fields(self):
        """Verifica que el modelo concreto herede los campos created_at y updated_at."""
        fields = [f.name for f in ConcreteTimeStampedModel._meta.get_fields()]
        self.assertIn('created_at', fields)
        self.assertIn('updated_at', fields)

        created_at_field = ConcreteTimeStampedModel._meta.get_field('created_at')
        updated_at_field = ConcreteTimeStampedModel._meta.get_field('updated_at')

        self.assertTrue(created_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)
