"""
Pruebas unitarias para el feed de descubrimiento y swipe de parejas (Issue #63).

Define la silueta de pruebas que el equipo debe expandir al implementar el controlador
y la capa de servicios.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class MatchFeedTests(TestCase):
    """Siluetas de pruebas para el feed de descubrimiento y evaluación de candidatos."""

    def setUp(self):
        self.user = User.objects.create_user(username='tutor_feed', password='password123')
        self.species = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Max',
            species=self.species,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
        )

    def test_match_feed_view_requires_authentication(self):
        """Verifica que el feed requiera sesión activa."""
        response = self.client.get(reverse('pets:match_feed'))
        self.assertEqual(response.status_code, 302)

    def test_like_candidate_endpoint_requires_post(self):
        """Silueta: Verifica que la acción de like rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_like_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_pass_candidate_endpoint_requires_post(self):
        """Silueta: Verifica que la acción de descarte rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_pass_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_report_candidate_endpoint_requires_post(self):
        """Silueta: Verifica que el reporte rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_report_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_candidate_filtering_by_opposite_gender_and_species(self):
        """
        Silueta pendiente para el equipo:
        Verificar que get_match_candidates excluya la propia mascota y filtre por sexo opuesto.
        """
        # TODO: Implementar por el equipo al conectar get_match_candidates con el ORM
        pass

    def test_mutual_match_detection_flow(self):
        """
        Silueta pendiente para el equipo:
        Verificar que cuando exista un like recíproco previo, se detecte is_match=True.
        """
        # TODO: Implementar por el equipo al conectar MatchRequest
        pass
