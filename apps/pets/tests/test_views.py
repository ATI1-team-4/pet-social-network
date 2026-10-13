import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

from apps.pets import views

User = get_user_model()


class PetsViewsTests(TestCase):
    """Pruebas unitarias para las rutas y vistas de la aplicación pets."""

    def setUp(self):
        self.user = User.objects.get(username='edwyn')
        self.client.force_login(self.user)
        from apps.pets.models import Pet, PetSpecies

        self.species = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')
        self.pet_toby = Pet.objects.create(
            owner=self.user,
            name='Toby',
            species=self.species,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date='2022-04-15',
            is_active_for_match=True,
            profile_color='coral',
        )
        self.pet_luna = Pet.objects.create(
            owner=self.user,
            name='Luna',
            species=self.species,
            breed='Golden Retriever',
            gender=Pet.Gender.HEMBRA,
            birth_date='2021-06-20',
            is_active_for_match=True,
            profile_color='lilac',
        )
        sofia = User.objects.get(username='sofia')
        self.cand_bella = Pet.objects.create(
            owner=sofia,
            name='Bella',
            species=self.species,
            breed='Pastor Australiano',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-10-12',
            is_active_for_match=True,
            profile_color='coral',
        )
        self.cand_simba = Pet.objects.create(
            owner=sofia,
            name='Simba',
            species=self.species,
            breed='Golden Retriever',
            gender=Pet.Gender.MACHO,
            birth_date='2022-05-10',
            is_active_for_match=True,
            profile_color='coral',
        )

    def test_unauthenticated_user_redirected_to_login(self):
        """Verifica que un usuario no autenticado sea redirigido a login al intentar acceder a la app."""
        self.client.logout()
        protected_urls = [
            reverse('pets:pet_management'),
            reverse('pets:pet_save'),
            reverse('pets:pet_delete', kwargs={'pet_id': '1234'}),
            reverse('pets:pet_select'),
            reverse('pets:pet_set_active'),
            reverse('pets:match_feed'),
            reverse('pets:match_interested'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'{reverse("accounts:login")}?next={url}')

    def test_pet_management_url_and_view(self):
        url = reverse('pets:pet_management')
        self.assertEqual(resolve(url).func, views.pet_management_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/pet_management.html')

    def test_pet_select_url_and_view(self):
        url = reverse('pets:pet_select')
        self.assertEqual(resolve(url).func, views.pet_select_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/pet_select.html')
        self.assertIn('pets', response.context)
        self.assertIn('active_pet', response.context)
        self.assertContains(response, 'Toby')
        self.assertContains(response, 'Luna')

        # Probar selección explícita mediante parámetro GET
        response_luna = self.client.get(url + '?selected=luna')
        self.assertEqual(response_luna.status_code, 200)
        self.assertEqual(response_luna.context['active_pet']['name'], 'Luna')

        # Verificar que otro usuario sólo ve sus propias mascotas y no las de edwyn
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_sofia = self.client.get(url)
        self.assertEqual(response_sofia.status_code, 200)
        self.assertContains(response_sofia, 'Bella')
        self.assertContains(response_sofia, 'Simba')
        self.assertNotContains(response_sofia, 'Toby')

    def test_match_feed_url_and_view(self):
        url = reverse('pets:match_feed')
        self.assertEqual(resolve(url).func, views.match_feed_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/match_feed.html')

    def test_match_interested_url_and_view(self):
        url = reverse('pets:match_interested')
        self.assertEqual(resolve(url).func, views.match_interested_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/match_interested.html')

    def test_pet_management_query_params(self):
        """Verifica la carga de mascotas por parámetro de consulta GET."""
        url = reverse('pets:pet_management') + '?pet=luna'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luna')

        url_new = reverse('pets:pet_management') + '?new=true'
        response_new = self.client.get(url_new)
        self.assertEqual(response_new.status_code, 200)
        self.assertContains(response_new, 'Registrar mascota')

    def test_pet_save_view(self):
        """Verifica el guardado y actualización de mascotas mediante la vista dedicada pet_save_view."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.pets.models import Pet

        save_url = reverse('pets:pet_save')
        response_save = self.client.post(save_url, {'name': 'Toby', 'pet_id': '1234'})
        self.assertRedirects(response_save, reverse('pets:pet_management'))

        # Rechazar solicitudes GET en pet_save_view (require_POST)
        response_get = self.client.get(save_url)
        self.assertEqual(response_get.status_code, 405)

        photo_file = SimpleUploadedFile(
            'dog.jpg', b'\x47\x49\x46\x38\x39\x61', content_type='image/jpeg'
        )
        response_photo = self.client.post(
            save_url,
            {
                'name': 'Maximus',
                'breed': 'Husky',
                'species': 'perro',
                'gender': 'M',
                'birth_date': '2023-01-01',
                'photo': photo_file,
            },
        )

        self.assertRedirects(response_photo, reverse('pets:pet_management'))
        saved_pet = Pet.objects.filter(owner=self.user, name='Maximus').first()
        self.assertIsNotNone(saved_pet)
        self.assertTrue(saved_pet.has_photo)
        self.assertTrue(
            saved_pet.photo.name.startswith(f'pets/user_{self.user.id}_pet_{saved_pet.id}_avatar_')
        )

    def test_pet_delete_view(self):
        """Verifica la eliminación de mascotas mediante la vista dedicada pet_delete_view."""
        from datetime import date

        from apps.pets.models import Pet, PetSpecies

        species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        pet = Pet.objects.create(
            owner=self.user,
            name='Max',
            species=species_dog,
            breed='Labrador',
            birth_date=date(2023, 1, 1),
            purpose=Pet.Purpose.BOTH,
        )
        url = reverse('pets:pet_delete', kwargs={'pet_id': str(pet.id)})

        # Rechazar solicitudes GET (require_POST)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Aceptar POST y eliminar
        response_post = self.client.post(url)
        self.assertRedirects(response_post, reverse('pets:pet_management'))
        self.assertFalse(Pet.objects.filter(id=pet.id).exists())

    def test_pet_toggle_goal_view(self):
        """Verifica la actualización asíncrona de objetivos en PetMatch (matching, socializing, adoption)."""
        url = reverse('pets:pet_toggle_goal')

        # Rechazar solicitudes GET
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Desactivar buscando pareja
        response_matching = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_matching', 'value': False}),
            content_type='application/json',
        )
        self.assertEqual(response_matching.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertFalse(self.pet_toby.is_matching)
        self.assertFalse(self.pet_toby.is_active_for_match)

        # Activar en adopción
        response_adoption = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_adoption', 'value': True}),
            content_type='application/json',
        )
        self.assertEqual(response_adoption.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertTrue(self.pet_toby.is_adoption)
        self.assertTrue(self.pet_toby.is_for_adoption)

        # Desactivar buscando socializar
        response_social = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_socializing', 'value': False}),
            content_type='application/json',
        )
        self.assertEqual(response_social.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertFalse(self.pet_toby.is_socializing)

        # Mascota ajena no modificable
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_forbidden = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_matching', 'value': True}),
            content_type='application/json',
        )
        self.assertEqual(response_forbidden.status_code, 404)

    def test_pet_update_certificate_view(self):
        """Verifica la actualización asíncrona del tipo de pedigrí y certificado (fci, tramite, sin_pedigri)."""
        url = reverse('pets:pet_update_certificate')

        # Rechazar solicitudes GET
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Cambiar a 'tramite'
        response_tramite = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'tramite'}),
            content_type='application/json',
        )
        self.assertEqual(response_tramite.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'tramite')
        self.assertEqual(self.pet_toby.certificate_type, 'En trámite')

        # Cambiar a 'sin_pedigri'
        response_sin = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'sin_pedigri'}),
            content_type='application/json',
        )
        self.assertEqual(response_sin.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'sin_pedigri')
        self.assertEqual(self.pet_toby.certificate_type, 'Sin pedigrí')

        # Cambiar a 'fci'
        response_fci = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'fci'}),
            content_type='application/json',
        )
        self.assertEqual(response_fci.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'fci')
        self.assertEqual(self.pet_toby.certificate_type, 'Certificado FCI')

        # Mascota ajena
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_forbidden = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'tramite'}),
            content_type='application/json',
        )
        self.assertEqual(response_forbidden.status_code, 404)

    def test_pet_set_active_view(self):
        """Verifica que la vista dedicada pet_set_active_view guarde en sesión y redirija al feed."""
        url = reverse('pets:pet_set_active')

        # Rechazar solicitudes GET (require_POST)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        response = self.client.post(url, {'selected_pet_id': '5678'})
        self.assertRedirects(response, reverse('pets:match_feed'))
        self.assertEqual(self.client.session.get('active_pet_id'), '5678')

    def test_match_feed_view_context_and_content(self):
        """Verifica que el feed de cruza cargue candidatos, color de perfil y enlaces."""
        url = reverse('pets:match_feed')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_pet', response.context)
        self.assertIn('candidates', response.context)
        self.assertIn('candidates_json', response.context)
        self.assertIn('interested_sidebar', response.context)

        # Verifica candidatos oficiales y enlaces de navegación requeridos
        self.assertContains(response, 'Bella')
        self.assertContains(response, 'Pastor Australiano')
        self.assertContains(response, reverse('pets:pet_select'))
        self.assertContains(response, reverse('pets:match_interested'))

        # Verifica que al consultar con ?pet=luna se aplique su color de perfil
        url_luna = reverse('pets:match_feed') + '?pet=luna'
        response_luna = self.client.get(url_luna)
        self.assertEqual(response_luna.status_code, 200)
        self.assertEqual(response_luna.context['active_pet']['name'], 'Luna')
        self.assertContains(response_luna, response_luna.context['active_pet']['profile_color_hex'])

    def test_match_interested_view_context_and_content(self):
        """Verifica que la bandeja de interesados cargue pretendientes, citas y enlaces."""
        url = reverse('pets:match_interested')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_suitor', response.context)
        self.assertIn('secondary_suitors', response.context)
        self.assertIn('confirmed_dates', response.context)

        # Verifica pretendiente destacado (Kira) y secundarias (Chloe, Maya)
        self.assertContains(response, 'Kira')
        self.assertContains(response, 'Pomerania Mini')
        self.assertContains(response, 'Chloe')
        self.assertContains(response, 'Maya')

        # Verifica citas confirmadas y enlace de retorno al feed
        self.assertContains(response, 'Citas confirmadas')
        self.assertContains(response, reverse('pets:match_feed'))
