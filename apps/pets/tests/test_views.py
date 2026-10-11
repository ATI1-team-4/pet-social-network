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

        photo_file = SimpleUploadedFile('dog.jpg', b'\x47\x49\x46\x38\x39\x61', content_type='image/jpeg')
        response_photo = self.client.post(save_url, {
            'name': 'Maximus',
            'breed': 'Husky',
            'species': 'perro',
            'gender': 'M',
            'birth_date': '2023-01-01',
            'photo': photo_file,
        })

        self.assertRedirects(response_photo, reverse('pets:pet_management'))
        saved_pet = Pet.objects.filter(owner=self.user, name='Maximus').first()
        self.assertIsNotNone(saved_pet)
        self.assertTrue(saved_pet.has_photo)
        self.assertTrue(saved_pet.photo.name.startswith(f'pets/user_{self.user.id}_pet_{saved_pet.id}_avatar_'))


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
