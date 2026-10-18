"""
Pruebas unitarias para el feed de descubrimiento y evaluación de parejas.

Verifica:
- Exploración de candidatos compatibles por especie, sexo opuesto y estado activo.
- Restricciones de autenticación y métodos HTTP requeridos en las acciones del feed.
- Registro de 'Me gusta' y detección de matches mutuos con transición de estados.
- Registro de descartes (pass) y reportes de usuario/contenido.
- Filtrado dinámico por preferencias de pedigrí, distancia máxima y propósito de encuentro.
- Contadores de solicitudes entrantes y pendientes reflejados en la vista.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile, UserReport
from apps.pets.models import MatchRequest, Pet, PetSpecies
from apps.pets.services import (
    calculate_candidate_compatibility,
    calculate_candidate_distance,
    calculate_candidate_distance_km,
    get_match_candidates,
    record_candidate_like,
    record_candidate_pass,
)

User = get_user_model()


class MatchFeedTests(TestCase):
    """Pruebas unitarias para el feed de descubrimiento y evaluación de candidatos."""

    def setUp(self):
        # Obtenemos los usuarios correspondientes a los desarrolladores del equipo
        self.user = User.objects.get(username='bryan')
        self.other_user = User.objects.get(username='oriana')
        self.species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.species_cat, _ = PetSpecies.objects.get_or_create(
            slug='gato',
            defaults={'name': 'Gato', 'icon_name': 'cat'},
        )

        # Mascota activa de Bryan (Macho, Perro, Labrador)
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

        # Mascota candidata de Oriana (Hembra, Perro, Labrador)
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
        # Comprobamos que el usuario no autenticado sea redirigido con código HTTP 302
        self.assertEqual(response.status_code, 302)

    def test_like_candidate_endpoint_requires_post(self):
        """Verifica que la acción de like rechace peticiones GET."""
        self.client.login(username='bryan', password='123456789')
        response = self.client.get(reverse('pets:match_like_candidate'))
        # Comprobamos que el servidor devuelva código HTTP 405 (método no permitido)
        self.assertEqual(response.status_code, 405)

    def test_pass_candidate_endpoint_requires_post(self):
        """Verifica que la acción de descarte rechace peticiones GET."""
        self.client.login(username='bryan', password='123456789')
        response = self.client.get(reverse('pets:match_pass_candidate'))
        # Comprobamos que el servidor devuelva código HTTP 405 (método no permitido)
        self.assertEqual(response.status_code, 405)

    def test_report_candidate_endpoint_requires_post(self):
        """Verifica que el reporte rechace peticiones GET."""
        self.client.login(username='bryan', password='123456789')
        response = self.client.get(reverse('pets:match_report_candidate'))
        # Comprobamos que el servidor devuelva código HTTP 405 (método no permitido)
        self.assertEqual(response.status_code, 405)

    def test_match_feed_validates_is_active_for_match(self):
        """Si la mascota activa no está habilitada para match debe redirigir a selección de mascota."""
        # Desactivamos la mascota para emparejamiento
        self.pet.is_active_for_match = False
        self.pet.save()

        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.get(reverse('pets:match_feed'))
        # Comprobamos que redirija al selector de mascotas
        self.assertRedirects(response, reverse('pets:pet_select'))

    def test_candidate_filtering_by_opposite_gender_and_species(self):
        """Verifica que get_match_candidates filtre por sexo opuesto y especie excluyendo no compatibles."""
        # Registramos un macho de la misma especie (debe ser excluido por ser del mismo sexo)
        pet_male_dog = Pet.objects.create(
            owner=self.other_user,
            name='Rocky',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Registramos una hembra de distinta especie (gata, debe ser excluida)
        pet_female_cat = Pet.objects.create(
            owner=self.other_user,
            name='Mia',
            species=self.species_cat,
            breed='Siamés',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Registramos una hembra del mismo dueño (debe excluirse por pertenecer a Bryan)
        own_female_dog = Pet.objects.create(
            owner=self.user,
            name='Luna',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
            is_active_for_match=True,
        )
        # Registramos una hembra marcada como inactiva para match (debe excluirse)
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

        # Verificamos que la candidata compatible Bella aparezca en la lista
        self.assertIn(self.cand_bella, candidates)
        # Comprobamos que la propia mascota no aparezca entre los candidatos
        self.assertNotIn(self.pet, candidates)
        # Comprobamos que el perro del mismo sexo sea excluido
        self.assertNotIn(pet_male_dog, candidates)
        # Comprobamos que animales de otra especie sean excluidos
        self.assertNotIn(pet_female_cat, candidates)
        # Comprobamos que mascotas del mismo tutor no aparezcan
        self.assertNotIn(own_female_dog, candidates)
        # Comprobamos que mascotas inactivas sean excluidas
        self.assertNotIn(inactive_female_dog, candidates)

    def test_candidate_exclusion_of_previously_evaluated(self):
        """Verifica que las mascotas ya evaluadas con like o descarte sean excluidas de la lista."""
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
        # Verificamos que ambas candidatas aparezcan inicialmente en la lista
        self.assertIn(self.cand_bella, candidates_initial)
        self.assertIn(cand_kira, candidates_initial)

        # Evaluamos a Bella con Like
        record_candidate_like(self.pet, self.cand_bella)

        # Evaluamos a Kira con Descarte (Pass)
        record_candidate_pass(self.pet, cand_kira)

        candidates_after = list(get_match_candidates(self.pet))
        # Comprobamos que las candidatas ya procesadas no vuelvan a presentarse
        self.assertNotIn(self.cand_bella, candidates_after)
        self.assertNotIn(cand_kira, candidates_after)

    def test_like_candidate_endpoint_without_prior_reciprocity(self):
        """Registrar me gusta vía AJAX cuando no hay interés previo crea la solicitud en estado PENDING."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_like_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        # Verificamos que la respuesta retorne código HTTP 200 (éxito)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Comprobamos que la operación sea exitosa y que aún no sea match mutuo
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['is_match'])

        # Comprobamos la creación del registro MatchRequest en la base de datos
        req = MatchRequest.objects.filter(from_pet=self.pet, to_pet=self.cand_bella).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)

    def test_mutual_match_detection_flow(self):
        """Cuando existe un like previo de la otra mascota se detecta match mutuo y ambos pasan a ACCEPTED."""
        # Bella le dio like previamente a Max
        MatchRequest.objects.create(
            from_pet=self.cand_bella,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_like_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        # Verificamos respuesta HTTP exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Comprobamos que el resultado indique éxito y confirme el match mutuo
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_match'])

        # Comprobamos que ambas solicitudes mutuas pasen a estado ACCEPTED
        out_req = MatchRequest.objects.get(from_pet=self.pet, to_pet=self.cand_bella)
        in_req = MatchRequest.objects.get(from_pet=self.cand_bella, to_pet=self.pet)
        self.assertEqual(out_req.status, MatchRequest.RequestStatus.ACCEPTED)
        self.assertEqual(in_req.status, MatchRequest.RequestStatus.ACCEPTED)

    def test_pass_candidate_endpoint(self):
        """Registrar descarte vía AJAX crea un registro en MatchRequest con estado REJECTED."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.post(
            reverse('pets:match_pass_candidate'),
            data={'candidate_id': self.cand_bella.id},
            content_type='application/json',
        )
        # Verificamos respuesta HTTP 200
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['candidate_id'], self.cand_bella.id)

        # Comprobamos que el registro quede guardado con estado REJECTED
        req = MatchRequest.objects.filter(from_pet=self.pet, to_pet=self.cand_bella).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, MatchRequest.RequestStatus.REJECTED)

    def test_report_candidate_endpoint(self):
        """Registrar reporte de candidato vía AJAX crea un registro en UserReport."""
        self.client.login(username='bryan', password='123456789')
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
        # Verificamos que la petición responda con código HTTP 200
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Comprobamos la creación del reporte en la base de datos
        report = UserReport.objects.filter(
            reported_by=self.user,
            reported_pet=self.cand_bella,
        ).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reported_user, self.other_user)
        self.assertEqual(report.reason, 'Fotografía no corresponde a una mascota real')
        self.assertEqual(report.status, UserReport.ReportStatus.PENDING)

    def test_match_feed_view_renders_context_and_template(self):
        """Verifica el renderizado de match_feed_view con contexto dinámico de candidatos reales."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.get(reverse('pets:match_feed'))
        # Verificamos que responda con código HTTP 200 (éxito)
        self.assertEqual(response.status_code, 200)
        # Comprobamos que Django utilice la plantilla HTML del feed de match
        self.assertTemplateUsed(response, 'pets/match_feed.html')

        # Verificamos que el contexto incluya la mascota activa y los candidatos
        self.assertIn('active_pet', response.context)
        self.assertIn('candidates', response.context)
        self.assertIn('candidates_json', response.context)
        # Comprobamos que el nombre y la raza aparezcan en el HTML de la página
        self.assertContains(response, 'Bella')
        self.assertContains(response, 'Labrador')

    def test_match_feed_filters_by_pedigree_preference(self):
        """Verifica el filtrado de candidatos según la preferencia de pedigrí."""
        # Configuramos pedigrí FCI para Bella
        self.cand_bella.certificate_type = 'Certificado FCI'
        self.cand_bella.certificate_number = 'FCI-VE-1100'
        self.cand_bella.save()

        # Registramos una candidata sin pedigrí
        cand_no_pedigree = Pet.objects.create(
            owner=self.other_user,
            name='Kira',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-04-10',
            is_active_for_match=True,
            certificate_type='Sin pedigrí',
            certificate_number='',
            profile_color='mint',
        )

        # Consultamos candidatos filtrando exclusivamente por con pedigrí
        cand_with = list(get_match_candidates(self.pet, filters={'has_pedigree': True}))
        # Verificamos que Bella esté incluida y Kira excluida
        self.assertIn(self.cand_bella, cand_with)
        self.assertNotIn(cand_no_pedigree, cand_with)

        # Consultamos candidatos filtrando exclusivamente por sin pedigrí
        cand_without = list(get_match_candidates(self.pet, filters={'without_pedigree': True}))
        # Verificamos que Kira esté incluida y Bella excluida
        self.assertIn(cand_no_pedigree, cand_without)
        self.assertNotIn(self.cand_bella, cand_without)

        # Consultamos candidatos sin restricción de pedigrí
        cand_both = list(get_match_candidates(self.pet))
        # Verificamos que ambas candidatas aparezcan en el resultado
        self.assertIn(self.cand_bella, cand_both)
        self.assertIn(cand_no_pedigree, cand_both)

        # Probamos la vista del feed pasando el parámetro GET para mascotas sin pedigrí
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        resp_without = self.client.get(reverse('pets:match_feed') + '?pedigree=without_pedigree')
        self.assertEqual(resp_without.status_code, 200)
        self.assertEqual(resp_without.context['pedigree_preference'], 'without_pedigree')
        self.assertEqual(self.client.session.get('match_pedigree_preference'), 'without_pedigree')
        candidates_ids = [c['id'] for c in resp_without.context['candidates']]
        self.assertIn(cand_no_pedigree.id, candidates_ids)
        self.assertNotIn(self.cand_bella.id, candidates_ids)

        # Probamos la vista del feed pasando el parámetro GET para mascotas con pedigrí
        resp_with = self.client.get(reverse('pets:match_feed') + '?pedigree=with_pedigree')
        self.assertEqual(resp_with.status_code, 200)
        self.assertEqual(resp_with.context['pedigree_preference'], 'with_pedigree')
        candidates_with_ids = [c['id'] for c in resp_with.context['candidates']]
        self.assertIn(self.cand_bella.id, candidates_with_ids)
        self.assertNotIn(cand_no_pedigree.id, candidates_with_ids)

    def test_calculate_candidate_compatibility_simplified(self):
        """Verifica el cálculo de compatibilidad basado en la combinación de sexo y raza."""
        # Sexo opuesto y misma raza (Labrador macho y hembra) debe dar 95%
        self.assertEqual(calculate_candidate_compatibility(self.pet, self.cand_bella), 95)

        # Sexo opuesto pero distinta raza (Hembra Beagle) debe dar 75%
        cand_diff_breed = Pet.objects.create(
            owner=self.other_user,
            name='Daisy',
            species=self.species_dog,
            breed='Beagle',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
        )
        self.assertEqual(calculate_candidate_compatibility(self.pet, cand_diff_breed), 75)

        # Mismo sexo y misma raza (Macho Labrador) debe dar 60%
        cand_same_sex_same_breed = Pet.objects.create(
            owner=self.other_user,
            name='Rocky',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
        )
        self.assertEqual(calculate_candidate_compatibility(self.pet, cand_same_sex_same_breed), 60)

        # Mismo sexo y distinta raza (Macho Beagle) debe dar 50%
        cand_same_sex_diff_breed = Pet.objects.create(
            owner=self.other_user,
            name='Buster',
            species=self.species_dog,
            breed='Beagle',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-01',
        )
        self.assertEqual(calculate_candidate_compatibility(self.pet, cand_same_sex_diff_breed), 50)

        # Distinta especie (Perro contra Gato) debe dar 0% de compatibilidad
        cand_cat = Pet.objects.create(
            owner=self.other_user,
            name='Michi',
            species=self.species_cat,
            breed='Siamés',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-01',
        )
        self.assertEqual(calculate_candidate_compatibility(self.pet, cand_cat), 0)

    def test_calculate_candidate_distance_gps_and_fallback(self):
        """Verifica el cálculo de distancia geográfica por fórmula de Haversine y fallback de municipio."""
        p1, _ = UserProfile.objects.get_or_create(user=self.user)
        p2, _ = UserProfile.objects.get_or_create(user=self.other_user)

        # Coordenadas aproximadas entre Chacao y Las Mercedes (~2.8 km)
        p1.latitude = 10.4990
        p1.longitude = -66.8480
        p1.save()

        p2.latitude = 10.4780
        p2.longitude = -66.8620
        p2.save()

        km = calculate_candidate_distance_km(self.pet, self.cand_bella)
        # Comprobamos que el cálculo de distancia en kilómetros esté cerca de 2.8 km
        self.assertAlmostEqual(km, 2.8, delta=0.5)
        dist_str = calculate_candidate_distance(self.pet, self.cand_bella)
        # Verificamos que la cadena formateada contenga la unidad km
        self.assertIn('km', dist_str)

        # Coordenadas muy próximas a menos de 500 metros
        p2.latitude = 10.4991
        p2.longitude = -66.8481
        p2.save()
        self.cand_bella.refresh_from_db()
        self.pet.refresh_from_db()
        self.assertEqual(
            calculate_candidate_distance(self.pet, self.cand_bella), 'A menos de 500 m'
        )

        # Caso sin coordenadas GPS pero con el mismo municipio asignado
        p1.latitude = None
        p1.longitude = None
        p1.municipality = 'Chacao'
        p1.save()

        p2.latitude = None
        p2.longitude = None
        p2.municipality = 'Chacao'
        p2.save()
        self.cand_bella.refresh_from_db()
        self.pet.refresh_from_db()

        # Comprobamos que el fallback por mismo municipio asigne 1.5 km
        self.assertEqual(calculate_candidate_distance_km(self.pet, self.cand_bella), 1.5)

    def test_get_match_candidates_filters_by_max_distance(self):
        """Verifica que get_match_candidates filtre candidatos según la distancia máxima solicitada."""
        p1, _ = UserProfile.objects.get_or_create(user=self.user)
        p2, _ = UserProfile.objects.get_or_create(user=self.other_user)

        # Bryan en Chacao
        p1.latitude = 10.4990
        p1.longitude = -66.8480
        p1.save()

        # Oriana en Las Mercedes (~2.8 km)
        p2.latitude = 10.4780
        p2.longitude = -66.8620
        p2.save()

        # María Paula como tutora distante en Los Teques (~28 km)
        maria = User.objects.get(username='maria')
        p3, _ = UserProfile.objects.get_or_create(user=maria)
        p3.latitude = 10.3440
        p3.longitude = -67.0420
        p3.save()

        cand_far = Pet.objects.create(
            owner=maria,
            name='Sasha',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-03-01',
            is_active_for_match=True,
        )

        # Filtro de 5 km: Bella (~2.8 km) debe incluirse y Sasha (~28 km) debe ser excluida
        cand_5km = list(get_match_candidates(self.pet, filters={'max_distance': 5}))
        self.assertIn(self.cand_bella, cand_5km)
        self.assertNotIn(cand_far, cand_5km)

        # Filtro de 35 km: Ambas candidatas deben estar incluidas en el rango
        cand_35km = list(get_match_candidates(self.pet, filters={'max_distance': 35}))
        self.assertIn(self.cand_bella, cand_35km)
        self.assertIn(cand_far, cand_35km)

        # Filtro restrictivo de 1 km: Ambas quedan fuera del límite de distancia
        cand_1km = list(get_match_candidates(self.pet, filters={'max_distance': 1}))
        self.assertNotIn(self.cand_bella, cand_1km)
        self.assertNotIn(cand_far, cand_1km)

    def test_match_feed_view_applies_max_distance_filter(self):
        """Verifica que match_feed_view procese el parámetro max_distance y lo guarde en sesión."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        response = self.client.get(reverse('pets:match_feed') + '?max_distance=15')
        # Verificamos respuesta HTTP exitosa con código 200
        self.assertEqual(response.status_code, 200)
        # Comprobamos que el contexto y la sesión contengan el valor de distancia seleccionado
        self.assertEqual(response.context['max_distance'], 15)
        self.assertEqual(self.client.session.get('match_max_distance'), 15)
        # Comprobamos que el texto del filtro aparezca en el HTML renderizado
        self.assertContains(response, '&lt; 15 km')

    def test_pet_select_view_has_only_action_buttons(self):
        """Verifica que la pantalla de selección contenga los botones de acción inmediata."""
        self.client.login(username='bryan', password='123456789')
        response = self.client.get(reverse('pets:pet_select'))
        # Verificamos que la página cargue correctamente con código 200
        self.assertEqual(response.status_code, 200)
        # Comprobamos la presencia de los botones principales en el contenido
        self.assertContains(response, 'Continuar a buscar pareja')
        self.assertContains(response, 'Ver mascotas interesadas')

    def test_reload_feed_clears_rejected_requests(self):
        """Verifica que el parámetro reload=true elimine los descartes salientes de la mascota activa."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        # Descartamos a Bella
        record_candidate_pass(self.pet, self.cand_bella)
        self.assertEqual(
            MatchRequest.objects.filter(
                from_pet=self.pet,
                to_pet=self.cand_bella,
                status=MatchRequest.RequestStatus.REJECTED,
            ).count(),
            1,
        )

        # Al consultar sin reload Bella no debe aparecer entre los candidatos
        response = self.client.get(reverse('pets:match_feed'))
        self.assertEqual(len(response.context['candidates']), 0)

        # Al consultar con reload=true se limpian los descartes y Bella reaparece
        response_reload = self.client.get(reverse('pets:match_feed') + '?reload=true')
        self.assertEqual(response_reload.status_code, 200)
        self.assertEqual(len(response_reload.context['candidates']), 1)
        self.assertEqual(response_reload.context['candidates'][0]['id'], self.cand_bella.id)
        # Comprobamos que ya no exista el registro con estado REJECTED
        self.assertFalse(
            MatchRequest.objects.filter(
                from_pet=self.pet,
                to_pet=self.cand_bella,
                status=MatchRequest.RequestStatus.REJECTED,
            ).exists()
        )

    def test_match_feed_view_applies_purpose_filter(self):
        """Verifica que match_feed_view aplique el filtro de propósito y lo preserve en sesión."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        self.cand_bella.is_socializing = False
        self.cand_bella.is_active_for_match = True
        self.cand_bella.save()

        # Registramos una mascota con propósito de juego o socialización
        cand_play = Pet.objects.create(
            owner=self.other_user,
            name='Daisy',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-06-15',
            is_active_for_match=True,
            is_socializing=True,
        )

        # Filtrar por búsqueda de pareja (mating)
        resp_mating = self.client.get(reverse('pets:match_feed') + '?purpose=mating')
        self.assertEqual(resp_mating.status_code, 200)
        candidate_ids = [c['id'] for c in resp_mating.context['candidates']]
        self.assertIn(self.cand_bella.id, candidate_ids)
        self.assertNotIn(cand_play.id, candidate_ids)

        # Filtrar por socialización o juego (play)
        resp_play = self.client.get(reverse('pets:match_feed') + '?purpose=play')
        self.assertEqual(resp_play.status_code, 200)
        play_ids = [c['id'] for c in resp_play.context['candidates']]
        self.assertIn(cand_play.id, play_ids)
        self.assertNotIn(self.cand_bella.id, play_ids)

    def test_match_feed_request_counters_alignment(self):
        """Verifica que los contadores del feed reflejen adecuadamente las solicitudes entrantes y totales."""
        self.client.login(username='bryan', password='123456789')
        session = self.client.session
        session['active_pet_id'] = str(self.pet.id)
        session.save()

        # Creamos una solicitud entrante pendiente y una aceptada hacia la mascota de Bryan
        MatchRequest.objects.create(
            from_pet=self.cand_bella,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        cand_luna = Pet.objects.create(
            owner=self.other_user,
            name='Luna2',
            species=self.species_dog,
            breed='Labrador',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-06-15',
            is_active_for_match=True,
        )
        MatchRequest.objects.create(
            from_pet=cand_luna,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.get(reverse('pets:match_feed'))
        # Verificamos respuesta HTTP exitosa
        self.assertEqual(response.status_code, 200)
        # Comprobamos que el contador de pendientes sea 1 y el total de solicitudes sea 2
        self.assertEqual(response.context['pending_interested_count'], 1)
        self.assertEqual(response.context['total_requests_count'], 2)
        # Verificamos que los textos con los contadores figuren en la respuesta HTML
        self.assertContains(response, '1 nuevas')
        self.assertContains(response, 'Ver todas las solicitudes (2)')
