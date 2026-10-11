"""
Pruebas unitarias para concertación de citas y agenda de encuentros caninos (Issue #65).

Define la silueta de pruebas que el equipo debe expandir al implementar el agendamiento,
validación de horarios y cancelación en services.py y views.py.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.pets.forms import ScheduleMeetupForm
from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class PetMeetupTests(TestCase):
    """Siluetas de pruebas para la concertación y cancelación de encuentros caninos."""

    def setUp(self):
        self.user = User.objects.create_user(username='tutor_citas', password='password123')
        self.species = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Zeus',
            species=self.species,
            breed='Husky',
            gender=Pet.Gender.MACHO,
            birth_date='2020-03-15',
        )

    def test_schedule_meetup_form_instantiation(self):
        """Silueta: Verifica la inicialización del formulario ScheduleMeetupForm."""
        form = ScheduleMeetupForm()
        self.assertIn('date', form.fields)
        self.assertIn('time', form.fields)
        self.assertIn('location_name', form.fields)

    def test_schedule_meetup_endpoint_requires_post(self):
        """Silueta: Verifica que el agendamiento rechace peticiones GET."""
        self.client.login(username='tutor_citas', password='password123')
        response = self.client.get(reverse('pets:schedule_meetup'))
        self.assertEqual(response.status_code, 405)

    def test_cancel_meetup_endpoint_requires_post(self):
        """Silueta: Verifica que la cancelación rechace peticiones GET."""
        self.client.login(username='tutor_citas', password='password123')
        response = self.client.get(reverse('pets:cancel_meetup', kwargs={'meetup_id': 1}))
        self.assertEqual(response.status_code, 405)

    def test_schedule_meetup_future_date_validation(self):
        """
        Silueta pendiente para el equipo:
        Verificar que no se permitan fechas ni horas pasadas al agendar encuentros.
        """
        # TODO: Implementar por el equipo en ScheduleMeetupForm.clean()
        pass

    def test_cancel_meetup_permission_and_state(self):
        """
        Silueta pendiente para el equipo:
        Verificar que solo los tutores involucrados puedan cancelar y el estado pase a CANCELLED.
        """
        # TODO: Implementar por el equipo al conectar cancel_pet_meetup
        pass
