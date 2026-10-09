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
            reverse('pets:pet_select'),
            reverse('pets:match_feed'),
            reverse('pets:match_interested'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

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

    def test_pet_management_post_save_and_delete(self):
        """Verifica el procesamiento de formularios POST en la gestión de mascotas."""
        url = reverse('pets:pet_management')
        response_save = self.client.post(url, {'action': 'save', 'name': 'Toby'})
        self.assertRedirects(response_save, url)

        response_del = self.client.post(url, {'action': 'delete', 'name': 'Toby'})
        self.assertRedirects(response_del, url)

    def test_pet_select_post_updates_session(self):
        """Verifica que la selección de mascota guarde en sesión y redirija al feed de cruza."""
        url = reverse('pets:pet_select')
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
