from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class InternationalizationTests(TestCase):
    """Pruebas para verificar la infraestructura de internacionalización (i18n)."""

    def setUp(self):
        # Obtenemos al desarrollador Edwyn como tutor de prueba
        self.user = User.objects.get(username='edwyn')
        self.client.force_login(self.user)
        self.species, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Simba',
            species=self.species,
            breed='Golden Retriever',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 5, 10),
            is_active_for_match=True,
        )

    def test_default_language_is_spanish(self):
        """Verifica que el idioma predeterminado del sistema sea español."""
        response = self.client.get(reverse('pets:pet_select'), headers={'host': 'localhost'})
        # Comprobamos respuesta HTTP exitosa con código 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que los textos de la interfaz aparezcan en español por defecto
        self.assertContains(response, 'Mis mascotas')
        self.assertContains(response, 'Seleccionar mascota')

    def test_switch_language_to_english_via_set_language(self):
        """Verifica que el cambio de idioma a inglés traduzca el navbar y las plantillas."""
        # Enviar petición POST al endpoint oficial de Django /i18n/setlang/
        response_switch = self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': reverse('pets:pet_select')},
            headers={'host': 'localhost'},
        )
        # Comprobamos que responda con código HTTP 302 (redirección hacia next)
        self.assertEqual(response_switch.status_code, 302)

        # Consultar la página con la cookie de idioma establecida
        response_en = self.client.get(reverse('pets:pet_select'), headers={'host': 'localhost'})
        self.assertEqual(response_en.status_code, 200)
        # Verificamos que los textos del navbar y de la vista se muestren traducidos en inglés
        self.assertContains(response_en, 'My pets')
        self.assertContains(response_en, 'Select pet')
        self.assertContains(response_en, 'Find a match')
        self.assertContains(response_en, 'Interested')
        self.assertContains(response_en, 'Terms of service')

    def test_pet_management_english_translations_and_sentence_case(self):
        """Verifica que pet_management traduzca al inglés en sentence case (incluyendo botón y modal de eliminar)."""
        # Cambiar el idioma a inglés enviando la preferencia a set_language
        self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': reverse('pets:pet_management')},
            headers={'host': 'localhost'},
        )

        # Solicitar la vista de gestión de mascotas con la sesión en inglés
        response_en = self.client.get(reverse('pets:pet_management'), headers={'host': 'localhost'})
        # Comprobamos respuesta HTTP 200
        self.assertEqual(response_en.status_code, 200)

        # Verificamos que los botones de acción y diálogos modales aparezcan traducidos en inglés
        self.assertContains(response_en, 'Delete pet')
        self.assertContains(response_en, 'Discard changes')
        self.assertContains(response_en, 'Preview')
        self.assertContains(response_en, 'Save changes')
        self.assertContains(response_en, 'Keep pet')
        self.assertContains(response_en, 'Delete')
