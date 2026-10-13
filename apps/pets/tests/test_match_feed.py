"""
Pruebas unitarias para el feed de descubrimiento y swipe de parejas (Issue #63).
Cubre:
- UC-08.1: Exploración de parejas compatibles (#40).
- UC-08.3: Condición de entrada al feed (#41).
- UC-14: Reportar usuario / Contenido (#14).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserReport
from apps.pets.models import MatchRequest, Pet, PetSpecies
from apps.pets.services import (
    get_match_candidates,
    record_candidate_like,
    record_candidate_pass,
)

User = get_user_model()


class MatchFeedTests(TestCase):
    """Pruebas unitarias para el feed de descubrimiento y evaluación de candidatos."""

    def setUp(self):
        self.user = User.objects.create_user(username='tutor_feed', password='password123')
        self.other_user = User.objects.create_user(username='tutor_other', password='password123')
        self.species_dog = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')
        self.species_cat = PetSpecies.objects.create(name='Gato', slug='gato', icon_name='cat')

        # Mascota activa del usuario de prueba (Macho, Perro, Labrador)
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Max',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
            is_active_for_match=True,
            profile_color='coral',
        )

        # Candidata compatible (Hembra, Perro, Labrador, tutor distinto)
        self.cand_bella = Pet.objects.create(
            owner=self.other_user,
            name='Bella',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-06-15',
            is_active_for_match=True,
            profile_color='lilac',
        )

    def test_match_feed_view_requires_authentication(self):
        """Verifica que el feed requiera sesión activa."""
        response = self.client.get(reverse('pets:match_feed'))
        self.assertEqual(response.status_code, 302)

    def test_like_candidate_endpoint_requires_post(self):
        """Verifica que la acción de like rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_like_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_pass_candidate_endpoint_requires_post(self):
        """Verifica que la acción de descarte rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_pass_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_report_candidate_endpoint_requires_post(self):
        """Verifica que el reporte rechace peticiones GET."""
        self.client.login(username='tutor_feed', password='password123')
        response = self.client.get(reverse('pets:match_report_candidate'))
        self.assertEqual(response.status_code, 405)

    def test_match_feed_validates_is_active_for_match(self):
        """
        Criterio de aceptación 2 (UC-08.3):
        Validar que si la mascota activa tiene is_active_for_match=False, redirija a selección de mascota.
        """
        self.pet.is_active_for_match = False
        self.pet.save()

        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.get(reverse('pets:match_feed'))
        self.assertRedirects(response, reverse('pets:pet_select'))

    def test_candidate_filtering_by_opposite_gender_and_species(self):
        """
        Criterio de aceptación 1 (UC-08.1):
        Verificar que get_match_candidates filtre por sexo opuesto y especie,
        excluyendo a la propia mascota, mascotas del mismo tutor y mascotas inactivas.
        """
        # Mascota macho (mismo sexo -> debe excluirse)
        pet_male_dog = Pet.objects.create(
            owner=self.other_user,
            name='Rocky',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Gata hembra (distinta especie -> debe excluirse)
        pet_female_cat = Pet.objects.create(
            owner=self.other_user,
            name='Mia',
            species=self.species_cat,
            breed='Siamés',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Perra hembra del mismo dueño (debe excluirse)
        own_female_dog = Pet.objects.create(
            owner=self.user,
            name='Luna',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Perra inactiva para match (debe excluirse)
        inactive_female_dog = Pet.objects.create(
            owner=self.other_user,
            name='Kira',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
            is_active_for_match=False,
        )

        candidates = list(get_match_candidates(self.pet))

        # Debe incluir a Bella
        self.assertIn(self.cand_bella, candidates)
        # No debe incluir candidatos no compatibles
        self.assertNotIn(self.pet, candidates)
        self.assertNotIn(pet_male_dog, candidates)
        self.assertNotIn(pet_female_cat, candidates)
        self.assertNotIn(own_female_dog, candidates)
        self.assertNotIn(inactive_female_dog, candidates)

    def test_candidate_exclusion_of_previously_evaluated(self):
        """
        Verificar que las mascotas ya evaluadas (con like previo o descarte)
        sean excluidas del queryset de get_match_candidates.
        """
        # Crear otra candidata
        cand_kira = Pet.objects.create(
            owner=self.other_user,
            name='Kira',
            species=self.species_dog,
            breed='Samoyedo',
            gender=Pet.Gender.HEMBRA,
            birth_date='2023-01-01',
            is_active_for_match=True,
        )

        candidates_initial = list(get_match_candidates(self.pet))
        self.assertIn(self.cand_bella, candidates_initial)
        self.assertIn(cand_kira, candidates_initial)

        # Evaluamos a Bella con Like
        record_candidate_like(self.pet, self.cand_bella)

        # Evaluamos a Kira con Pass / Descarte
        record_candidate_pass(self.pet, cand_kira)

        candidates_after = list(get_match_candidates(self.pet))
        self.assertNotIn(self.cand_bella, candidates_after)
        self.assertNotIn(cand_kira, candidates_after)

    def test_like_candidate_endpoint_without_prior_reciprocity(self):
        """
        Criterio de aceptación 4:
        Registrar 'Me gusta' vía AJAX cuando no hay interés previo -> status=PENDING, is_match=False.
        """
        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_like_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['is_match'])

        # Verificar persistencia en MatchRequest
        req = MatchRequest.objects.filter(from_pet=self.pet, to_pet=self.cand_bella).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)

    def test_mutual_match_detection_flow(self):
        """
        Criterio de aceptación 5:
        Verificar que cuando exista un like recíproco previo de Bella hacia Max,
        al darle like desde Max se detecte is_match=True y ambos registros transicionen a ACCEPTED.
        """
        # Bella le dio like previamente a Max
        MatchRequest.objects.create(
            from_pet=self.cand_bella,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_like_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_match'])

        # Ambas solicitudes deben haber pasado a ACCEPTED
        out_req = MatchRequest.objects.get(from_pet=self.pet, to_pet=self.cand_bella)
        in_req = MatchRequest.objects.get(from_pet=self.cand_bella, to_pet=self.pet)
        self.assertEqual(out_req.status, MatchRequest.RequestStatus.ACCEPTED)
        self.assertEqual(in_req.status, MatchRequest.RequestStatus.ACCEPTED)

    def test_pass_candidate_endpoint(self):
        """
        Criterio de aceptación 6:
        Registrar descarte vía AJAX -> crea registro en MatchRequest con status=REJECTED.
        """
        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_pass_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['candidate_id'], self.cand_bella.id)

        req = MatchRequest.objects.filter(from_pet=self.pet, to_pet=self.cand_bella).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, MatchRequest.RequestStatus.REJECTED)

    def test_report_candidate_endpoint(self):
        """
        Criterio de aceptación 8:
        Conectar reporte de candidato vía AJAX -> crea registro en UserReport.
        """
        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_report_candidate'),
            data={
                'candidate_id': self.cand_bella.id,
                'reason': 'Fotografía no corresponde a una mascota real',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        report = UserReport.objects.filter(
            reported_by=self.user,
            reported_pet=self.cand_bella,
        ).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reported_user, self.other_user)
        self.assertEqual(report.reason, 'Fotografía no corresponde a una mascota real')
        self.assertEqual(report.status, UserReport.ReportStatus.PENDING)

    def test_match_feed_view_renders_context_and_template(self):
        """
        Verifica el renderizado de match_feed_view (GET) con contexto dinámico de candidatos reales.
        """
        self.client.login(username='tutor_feed', password='password123')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.get(reverse('pets:match_feed'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/match_feed.html')

        self.assertIn('active_pet', response.context)
        self.assertIn('candidates', response.context)
        self.assertIn('candidates_json', response.context)
        self.assertIn('current_candidate', response.context)

        # Verificar que Bella aparezca en la respuesta HTML
        self.assertContains(response, 'Bella')
        self.assertContains(response, 'Labrador')
