from django.test import TestCase
from django.urls import resolve, reverse

from apps.accounts import views


class AccountsViewsTests(TestCase):
    """Pruebas unitarias para las rutas y vistas de la aplicación accounts."""

    def test_login_url_and_view(self):
        url = reverse('accounts:login')
        self.assertEqual(resolve(url).func, views.login_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_register_url_and_view(self):
        url = reverse('accounts:register')
        self.assertEqual(resolve(url).func, views.register_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_password_reset_url_and_view(self):
        url = reverse('accounts:password_reset')
        self.assertEqual(resolve(url).func, views.password_reset_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/password_reset.html')

    def test_logout_url_and_redirect(self):
        url = reverse('accounts:logout')
        self.assertEqual(resolve(url).func, views.logout_view)
        response = self.client.get(url)
        self.assertRedirects(response, reverse('core:home'))

    def test_profile_url_and_view(self):
        url = reverse('accounts:profile')
        self.assertEqual(resolve(url).func, views.profile_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/user_profile.html')
