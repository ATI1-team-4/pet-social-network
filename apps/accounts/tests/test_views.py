from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

from apps.accounts import views

User = get_user_model()


class AccountsViewsTests(TestCase):
    """Pruebas unitarias para las rutas y vistas de la aplicación accounts."""

    def test_login_url_and_view(self):
        """Verifica la resolución de URL, código HTTP y plantilla del formulario de inicio de sesión."""
        url = reverse('accounts:login')
        self.assertEqual(resolve(url).func, views.login_view)
        response = self.client.get(url)
        # Comprobamos que responda con código HTTP 200 (éxito)
        self.assertEqual(response.status_code, 200)
        # Verificamos que Django use la plantilla HTML del inicio de sesión
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_redirects_to_next_url(self):
        """El inicio de sesión redirige a next_url si es seguro; de lo contrario a pet_select."""
        login_data = {
            'email': 'edwyn@petly.com',
            'password': '123456789',
            'next': '/accounts/profile/',
        }
        response = self.client.post(reverse('accounts:login'), login_data)
        # Comprobamos que redirija al parámetro next tras autenticarse con éxito
        self.assertRedirects(response, '/accounts/profile/')

        # Usuario autenticado que navega a login con next
        user = User.objects.get(username='edwyn')
        self.client.force_login(user)
        response_auth = self.client.get(f'{reverse("accounts:login")}?next=/accounts/profile/')
        self.assertRedirects(response_auth, '/accounts/profile/')
        self.client.logout()

        # Evitar redirecciones abiertas a dominios externos no seguros
        unsafe_data = {
            'email': 'edwyn@petly.com',
            'password': '123456789',
            'next': 'https://sitio-externo-malicioso.com/robo-token',
        }
        response_unsafe = self.client.post(reverse('accounts:login'), unsafe_data)
        # Verificamos que ante una URL externa peligrosa descarte la redirección y lleve a selección de mascota
        self.assertRedirects(response_unsafe, reverse('pets:pet_select'), target_status_code=302)

    def test_register_url_and_view(self):
        """Verifica la resolución de URL, código HTTP y plantilla del registro."""
        url = reverse('accounts:register')
        self.assertEqual(resolve(url).func, views.register_view)
        response = self.client.get(url)
        # Comprobamos respuesta HTTP 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que Django renderice la plantilla de registro
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_redirects_to_next_url(self):
        """El registro exitoso redirige al parámetro next si es seguro."""
        register_data = {
            'full_name': 'Stefany Martínez',
            'email': 'stefany.nueva@petly.com',
            'phone_prefix': '+58',
            'phone': '4143334455',
            'id_type': 'V',
            'id_number': '30111222',
            'password': 'Password123',
            'password_confirm': 'Password123',
            'next': '/accounts/profile/',
        }
        response = self.client.post(
            f'{reverse("accounts:register")}?next=/accounts/profile/', register_data
        )
        # Comprobamos que tras registrarse se redirija a la ruta indicada en next
        self.assertRedirects(response, '/accounts/profile/')

    def test_password_reset_url_and_view(self):
        """Verifica la plantilla y respuesta del formulario de recuperación de contraseña."""
        url = reverse('accounts:password_reset')
        self.assertEqual(resolve(url).func, views.password_reset_view)
        response = self.client.get(url)
        # Comprobamos respuesta HTTP 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que utilice la plantilla de reseteo de contraseña
        self.assertTemplateUsed(response, 'accounts/password_reset.html')

    def test_logout_url_and_redirect(self):
        """Verifica que el cierre de sesión redirija a la página principal."""
        url = reverse('accounts:logout')
        self.assertEqual(resolve(url).func, views.logout_view)
        response = self.client.get(url)
        # Comprobamos que el logout redirija al home
        self.assertRedirects(response, reverse('core:home'))

    def test_profile_url_and_view(self):
        """Verifica restricciones de acceso y renderizado del perfil de usuario."""
        url = reverse('accounts:profile')
        self.assertEqual(resolve(url).func, views.profile_view)

        # Usuario no autenticado es redirigido a login
        response = self.client.get(url)
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={url}')

        # Usuario autenticado accede exitosamente
        user = User.objects.get(username='edwyn')
        self.client.force_login(user)
        response_auth = self.client.get(url)
        self.assertEqual(response_auth.status_code, 200)
        # Verificamos la plantilla del perfil
        self.assertTemplateUsed(response_auth, 'accounts/user_profile.html')
        # Comprobamos que el contexto contenga las mascotas del usuario
        self.assertIn('user_pets', response_auth.context)
        self.assertEqual(response_auth.context['pets_count'], user.pets.count())
        self.assertIn('active_connections_count', response_auth.context)

    def test_profile_save_view_post_updates_profile(self):
        """Verifica la actualización de los datos del perfil de usuario mediante POST."""
        url = reverse('accounts:profile_save')
        self.assertEqual(resolve(url).func, views.profile_save_view)

        user = User.objects.get(username='edwyn')
        self.client.force_login(user)

        response = self.client.post(
            url,
            {
                'full_name': 'Edwyn Jesús',
                'email': 'edwyn.updated@petly.com',
                'phone': '+58 412 111 2233',
                'state': 'Miranda',
                'municipality': 'Chacao',
                'neighborhood': 'Los Palos Grandes',
                'favorite_color': 'Azul Eléctrico',
                'latitude': '10.4990',
                'longitude': '-66.8480',
            },
        )
        # Comprobamos que tras actualizar datos redirija al perfil
        self.assertRedirects(response, reverse('accounts:profile'))
        user.refresh_from_db()
        # Verificamos que los datos modificados se hayan guardado en la base de datos
        self.assertEqual(user.first_name, 'Edwyn')
        self.assertEqual(user.last_name, 'Jesús')
        self.assertEqual(user.profile.phone_number, '+58 412 111 2233')
        self.assertEqual(user.profile.state, 'Miranda')
        self.assertEqual(user.profile.municipality, 'Chacao')
        self.assertEqual(user.profile.neighborhood, 'Los Palos Grandes')
        self.assertEqual(user.profile.city, 'Chacao')
        self.assertEqual(user.profile.favorite_color, 'Azul Eléctrico')
        self.assertEqual(user.profile.latitude, 10.4990)
        self.assertEqual(user.profile.longitude, -66.8480)

    def test_password_reset_request_view(self):
        """La solicitud de recuperación de contraseña procesa el correo y redirige al login."""
        response = self.client.post(
            reverse('accounts:password_reset'),
            {'email': 'bryan@petly.com'},
        )
        # Comprobamos que tras enviar el correo de recuperación redirija a la pantalla de login
        self.assertRedirects(response, reverse('accounts:login'))
