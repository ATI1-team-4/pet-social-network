from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import resolve, reverse

from apps.accounts import views
from apps.accounts.models import UserProfile
from apps.core.models import AuditLog

User = get_user_model()


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


class AccountsSecurityAndAuditTests(TestCase):
    """Pruebas para el módulo de seguridad, roles, permisos y AuditLog."""

    def test_security_roles_exist(self):
        """Verifica que los grupos Tutor y Administrador existan en la base de datos."""
        self.assertTrue(Group.objects.filter(name='Tutor').exists())
        self.assertTrue(Group.objects.filter(name='Administrador').exists())

    def test_register_user_creates_tutor_role_and_audit_log(self):
        """El registro exitoso crea el perfil, asigna el grupo Tutor y registra en AuditLog."""
        register_data = {
            'full_name': 'Carlos Mendoza',
            'email': 'carlos@petly.com',
            'phone_prefix': '+58',
            'phone': '4249998877',
            'id_type': 'V',
            'id_number': '29999888',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        response = self.client.post(reverse('accounts:register'), register_data)
        self.assertRedirects(response, reverse('pets:pet_select'))

        user = User.objects.filter(email='carlos@petly.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'Carlos')
        self.assertEqual(user.last_name, 'Mendoza')

        # Verificar rol asignado
        self.assertTrue(user.groups.filter(name='Tutor').exists())

        # Verificar perfil creado
        profile = UserProfile.objects.filter(user=user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.id_number, '29999888')
        self.assertEqual(profile.phone_number, '4249998877')

        # Verificar AuditLog generado
        register_log = AuditLog.objects.filter(action='REGISTER_SUCCESS', user=user).first()
        self.assertIsNotNone(register_log)
        self.assertIn('Registro de nuevo tutor', register_log.details)

    def test_register_duplicate_id_number_rejected(self):
        """El registro rechaza cédulas duplicadas que ya pertenezcan a otro tutor."""
        duplicate_data = {
            'full_name': 'Otro Tutor',
            'email': 'otro.tutor@petly.com',
            'phone_prefix': '+58',
            'phone': '4140001122',
            'id_type': 'V',
            'id_number': '27456789',  # Cédula existente de Edwyn en dev_users
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        response = self.client.post(reverse('accounts:register'), duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'id_number',
            'Ya existe una cuenta registrada con este documento de identidad (V-27456789).',
        )

    def test_register_same_id_number_different_type_allowed(self):
        """Un tutor extranjero (E) puede registrarse con el mismo número que un venezolano (V)."""
        foreigner_data = {
            'full_name': 'Hans Muller',
            'email': 'hans.muller@petly.com',
            'phone_prefix': '+58',
            'phone': '4125556677',
            'id_type': 'E',
            'id_number': '27456789',  # Mismo número que Edwyn pero con tipo 'E'
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        response = self.client.post(reverse('accounts:register'), foreigner_data)
        self.assertRedirects(response, reverse('pets:pet_select'))

        user = User.objects.filter(email='hans.muller@petly.com').first()
        self.assertIsNotNone(user)
        profile = UserProfile.objects.filter(user=user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.id_type, 'E')
        self.assertEqual(profile.id_number, '27456789')

    def test_login_success_creates_audit_log(self):
        """El inicio de sesión exitoso crea un registro LOGIN_SUCCESS en AuditLog."""
        login_data = {
            'email': 'edwyn@petly.com',
            'password': '123456789',
            'remember_me': True,
        }
        response = self.client.post(reverse('accounts:login'), login_data)
        self.assertRedirects(response, reverse('pets:pet_select'))

        user = User.objects.get(username='edwyn')
        login_log = AuditLog.objects.filter(action='LOGIN_SUCCESS', user=user).first()
        self.assertIsNotNone(login_log)
        self.assertIn('edwyn', login_log.details)

    def test_login_failed_creates_audit_log(self):
        """Un intento fallido de autenticación genera un evento LOGIN_FAILED en AuditLog."""
        bad_data = {
            'email': 'noexiste@petly.com',
            'password': 'WrongPassword123',
        }
        response = self.client.post(reverse('accounts:login'), bad_data)
        self.assertEqual(response.status_code, 200)

        failed_log = AuditLog.objects.filter(action='LOGIN_FAILED').first()
        self.assertIsNotNone(failed_log)
        self.assertIn('noexiste@petly.com', failed_log.details)

    def test_logout_creates_audit_log(self):
        """El cierre de sesión genera un evento LOGOUT en AuditLog."""
        user = User.objects.get(username='oriana')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('core:home'))

        logout_log = AuditLog.objects.filter(action='LOGOUT', user=user).first()
        self.assertIsNotNone(logout_log)

    def test_password_reset_request_view(self):
        """La solicitud de recuperación de contraseña procesa el formulario y redirige."""
        response = self.client.post(
            reverse('accounts:password_reset'),
            {'email': 'bryan@petly.com'},
        )
        self.assertRedirects(response, reverse('accounts:login'))
