"""
Pruebas unitarias para la bandeja de interesados y solicitudes de emparejamiento (Issue #64).

Define la silueta de pruebas que el equipo debe expandir al implementar los controladores
y la lógica de transición de estados en services.py.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class MatchInterestedTests(TestCase):
    """Siluetas de pruebas para la gestión de solicitudes e interesados."""

    def setUp(self):
        self.user = User.objects.create_user(username='tutor_interesados', password='password123')
        self.species = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Rocky',
            species=self.species,
            breed='Boxer',
            gender=Pet.Gender.MACHO,
            birth_date='2021-05-10',
        )

    def test_interested_view_requires_authentication(self):
        """Verifica que la pantalla de interesados requiera autenticación."""
        response = self.client.get(reverse('pets:match_interested'))
        self.assertEqual(response.status_code, 302)

    def test_accept_request_endpoint_requires_post(self):
        """Silueta: Verifica que la aceptación de match rechace peticiones GET."""
        self.client.login(username='tutor_interesados', password='password123')
        response = self.client.get(reverse('pets:match_accept_request', kwargs={'request_id': 1}))
        self.assertEqual(response.status_code, 405)

    def test_reject_request_endpoint_requires_post(self):
        """Silueta: Verifica que el descarte de match rechace peticiones GET."""
        self.client.login(username='tutor_interesados', password='password123')
        response = self.client.get(reverse('pets:match_reject_request', kwargs={'request_id': 1}))
        self.assertEqual(response.status_code, 405)

    def test_send_initial_message_endpoint_requires_post(self):
        """Silueta: Verifica que el envío de mensaje inicial rechace peticiones GET."""
        self.client.login(username='tutor_interesados', password='password123')
        response = self.client.get(reverse('pets:send_initial_message', kwargs={'request_id': 1}))
        self.assertEqual(response.status_code, 405)

    def test_tab_counters_calculation(self):
        """
        Silueta pendiente para el equipo:
        Verificar el cálculo dinámico de contadores para 'Todos', 'Interesados' y 'Mis solicitudes'.
        """
        # TODO: Implementar por el equipo al integrar get_requests_tab_counters
        pass

    def test_accept_match_request_transition(self):
        """
        Silueta pendiente para el equipo:
        Verificar que aceptar una solicitud actualice MatchRequest a 'accepted'.
        """
        # TODO: Implementar por el equipo al conectar accept_match_request
        pass
