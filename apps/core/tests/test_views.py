from django.test import TestCase
from django.urls import resolve, reverse

from apps.core import views


class HomeViewTests(TestCase):
    """Pruebas unitarias para la vista de inicio."""

    def test_home_url_resolves_to_home_view(self):
        """Verifica que la URL raíz resuelva a la función home."""
        resolver = resolve('/')
        # Verificamos que la URL raíz apunte a la función de vista views.home
        self.assertEqual(resolver.func, views.home)

    def test_home_page_status_code(self):
        """Verifica que la página de inicio responda exitosamente con código HTTP 200."""
        response = self.client.get(reverse('core:home'))
        # Comprobamos que el código de estado HTTP sea 200 (éxito)
        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_templates(self):
        """Verifica que se rendericen las plantillas correctas (core/home.html y base.html)."""
        response = self.client.get(reverse('core:home'))
        # Comprobamos que Django utilice la plantilla específica del home y la plantilla base
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_home_page_contains_brand_title(self):
        """Verifica que el contenido de la página contenga el nombre Petly."""
        response = self.client.get(reverse('core:home'))
        # Comprobamos que la palabra 'Petly' aparezca dentro del contenido HTML
        self.assertContains(response, 'Petly')

    def test_home_page_authenticated_redirects_to_pet_select(self):
        """Verifica que un usuario autenticado que ingrese al inicio sea redirigido a seleccionar mascota."""
        from datetime import date

        from django.contrib.auth import get_user_model

        from apps.pets.models import Pet, PetSpecies

        # Obtenemos al usuario Edwyn e iniciamos su sesión
        user = get_user_model().objects.get(username='edwyn')
        self.client.force_login(user)

        # Registramos una mascota activa para el usuario
        species, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        Pet.objects.create(
            owner=user,
            name='Simba',
            species=species,
            breed='Golden Retriever',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 5, 10),
            is_active_for_match=True,
        )

        response = self.client.get(reverse('core:home'))
        # Comprobamos que el usuario con sesión sea redirigido a la pantalla de selección de mascota
        self.assertRedirects(response, reverse('pets:pet_select'))
