from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.forms import LoginForm, RegisterForm

User = get_user_model()


class LoginFormTests(TestCase):
    """Pruebas unitarias para el formulario de inicio de sesión."""

    def test_login_form_valido_con_credenciales_completas(self):
        """Acepta datos cuando el correo y la contraseña están presentes."""
        datos = {
            'email': 'edwyn@petly.com',
            'password': 'Password123',
            'remember_me': True,
        }
        form = LoginForm(data=datos)
        # Comprobamos que el formulario apruebe todas las validaciones (is_valid=True)
        self.assertTrue(form.is_valid())

    def test_login_form_invalido_sin_correo_o_clave(self):
        """Rechaza el envío si falta el usuario o la contraseña."""
        form_sin_correo = LoginForm(data={'password': 'Password123'})
        # Comprobamos que el formulario sea rechazado
        self.assertFalse(form_sin_correo.is_valid())
        # Verificamos que el error se concentre en el campo 'email'
        self.assertIn('email', form_sin_correo.errors)

        form_sin_clave = LoginForm(data={'email': 'edwyn@petly.com'})
        # Comprobamos que el formulario sea rechazado
        self.assertFalse(form_sin_clave.is_valid())
        # Verificamos que el error se concentre en el campo 'password'
        self.assertIn('password', form_sin_clave.errors)


class RegisterFormTests(TestCase):
    """Pruebas de validación para el registro de nuevos tutores."""

    def test_registro_valido_con_datos_correctos(self):
        """Valida exitosamente cuando todos los campos cumplen las reglas de negocio."""
        datos = {
            'full_name': 'María Paula Herrero',
            'email': 'maria.nueva@petly.com',
            'phone_prefix': '+58',
            'phone': '4141234567',
            'id_type': 'V',
            'id_number': '31999888',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que el formulario sea válido
        self.assertTrue(form.is_valid())

    def test_registro_rechaza_contrasenas_distintas(self):
        """No permite el registro si la confirmación de contraseña no coincide."""
        datos = {
            'full_name': 'Oriana Arellano',
            'email': 'oriana.mismatch@petly.com',
            'phone_prefix': '+58',
            'phone': '4141234567',
            'id_type': 'V',
            'id_number': '31999889',
            'password': 'Password123',
            'password_confirm': 'OtraClaveDistinta',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que rechace el formulario
        self.assertFalse(form.is_valid())
        # Verificamos que se indique el error en la confirmación de contraseña
        self.assertIn('password_confirm', form.errors)

    def test_registro_rechaza_correo_duplicado(self):
        """Evita registrar dos cuentas con la misma dirección de correo electrónico."""
        # Usamos el correo del usuario Edwyn que ya existe en la base de datos
        datos = {
            'full_name': 'Edwyn Guzmán Duplicado',
            'email': 'edwyn@petly.com',
            'phone_prefix': '+58',
            'phone': '4129990011',
            'id_type': 'V',
            'id_number': '32000111',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que no se permita el registro
        self.assertFalse(form.is_valid())
        # Verificamos que el error corresponda a email duplicado
        self.assertIn('email', form.errors)

    def test_registro_rechaza_cedula_duplicada_del_mismo_tipo(self):
        """Rechaza el formulario si ya existe un tutor con el mismo tipo y número de cédula."""
        # Intentamos registrar la misma cédula venezolana de Edwyn (V-27456789)
        datos = {
            'full_name': 'Tutor Con Misma Cédula',
            'email': 'otro.correo@petly.com',
            'phone_prefix': '+58',
            'phone': '4145556677',
            'id_type': 'V',
            'id_number': '27456789',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que el formulario sea rechazado
        self.assertFalse(form.is_valid())
        # Verificamos que el error se marque en el campo 'id_number'
        self.assertIn('id_number', form.errors)

    def test_registro_permite_misma_cedula_con_tipo_extranjero(self):
        """Permite que un tutor extranjero use el mismo número que uno venezolano."""
        # El número 27456789 existe como venezolano (V), pero con tipo extranjero (E) es permitido
        datos = {
            'full_name': 'Hans Schmidt',
            'email': 'hans.schmidt@petly.com',
            'phone_prefix': '+58',
            'phone': '4128889900',
            'id_type': 'E',
            'id_number': '27456789',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que el formulario sea aceptado con éxito
        self.assertTrue(form.is_valid())

    def test_registro_rechaza_cedula_con_letras(self):
        """La cédula para venezolanos y extranjeros debe contener únicamente números."""
        datos = {
            'full_name': 'Sofía Marcano',
            'email': 'sofia.invalida@petly.com',
            'phone_prefix': '+58',
            'phone': '4149998877',
            'id_type': 'V',
            'id_number': '27ABC456',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que falle la validación ante caracteres no numéricos
        self.assertFalse(form.is_valid())
        # Verificamos el error en el campo 'id_number'
        self.assertIn('id_number', form.errors)

    def test_registro_rechaza_contrasena_sin_numeros(self):
        """La contraseña debe contener al menos un número según las reglas del sistema."""
        datos = {
            'full_name': 'Bryan Silva',
            'email': 'bryan.sin_numero@petly.com',
            'phone_prefix': '+58',
            'phone': '4149998877',
            'id_type': 'V',
            'id_number': '31222333',
            'password': 'SoloLetrasSinNumero',
            'password_confirm': 'SoloLetrasSinNumero',
        }
        form = RegisterForm(data=datos)
        # Comprobamos que el formulario rechace una contraseña sin dígitos
        self.assertFalse(form.is_valid())
        # Verificamos que se reporte el error en el campo 'password'
        self.assertIn('password', form.errors)
