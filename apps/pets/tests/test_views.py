from django.test import TestCase
from django.urls import resolve, reverse

from apps.pets import views


class PetsViewsTests(TestCase):
    """Pruebas unitarias para las rutas y vistas de la aplicación pets."""

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
        self.assertContains(response_new, 'Registrar Mascota')

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
