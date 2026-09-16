from django.test import TestCase
from django.urls import resolve, reverse

from apps.core import views


class HomeViewTests(TestCase):
    """Pruebas unitarias para la vista de inicio."""

    def test_home_url_resolves_to_home_view(self):
        """Verifica que la URL raíz resuelva a la función home."""
        resolver = resolve('/')
        self.assertEqual(resolver.func, views.home)

    def test_home_page_status_code(self):
        """Verifica que la página de inicio responda exitosamente con código HTTP 200."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_templates(self):
        """Verifica que se rendericen las plantillas correctas (core/home.html y base.html)."""
        response = self.client.get(reverse('core:home'))
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_home_page_contains_brand_title(self):
        """Verifica que el contenido de la página contenga el nombre Petly."""
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'Bienvenido a Petly')
