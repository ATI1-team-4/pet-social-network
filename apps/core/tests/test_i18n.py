from django.test import TestCase
from django.urls import reverse


class InternationalizationTests(TestCase):
    """Pruebas para verificar la infraestructura de internacionalización (i18n)."""

    def test_default_language_is_spanish(self):
        """Verifica que el idioma predeterminado del sistema sea español."""
        response = self.client.get(reverse('pets:pet_select'), headers={'host': 'localhost'})
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response_switch.status_code, 302)

        # Consultar la página con la cookie de idioma establecida
        response_en = self.client.get(reverse('pets:pet_select'), headers={'host': 'localhost'})
        self.assertEqual(response_en.status_code, 200)
        self.assertContains(response_en, 'My pets')
        self.assertContains(response_en, 'Select Pet')
        self.assertContains(response_en, 'Find a Match')
        self.assertContains(response_en, 'Interested')
        self.assertContains(response_en, 'Terms of service')
