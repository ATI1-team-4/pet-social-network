from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile
from apps.core.models import AuditLog

User = get_user_model()


class AccountsSecurityAndRolesTests(TestCase):
    """Pruebas para los roles de usuario del sistema (Tutor y Administrador)."""

    def test_existencia_de_roles_del_sistema(self):
        """Los grupos base Tutor y Administrador deben existir en la base de datos."""
        # Verificamos que el grupo de seguridad 'Tutor' exista en el sistema
        self.assertTrue(Group.objects.filter(name='Tutor').exists())
        # Verificamos que el grupo 'Administrador' esté presente
        self.assertTrue(Group.objects.filter(name='Administrador').exists())

    def test_nuevo_registro_asigna_rol_tutor(self):
        """Al registrarse, el usuario recibe automáticamente el rol de Tutor."""
        # Enviamos los datos para registrar a un nuevo tutor en el sistema
        datos = {
            'full_name': 'Bryan Silva Prueba',
            'email': 'bryan.seguridad@petly.com',
            'phone_prefix': '+58',
            'phone': '4249998877',
            'id_type': 'V',
            'id_number': '29999888',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        self.client.post(reverse('accounts:register'), datos)

        # Buscamos al usuario creado y comprobamos que se haya persistido
        usuario = User.objects.filter(email='bryan.seguridad@petly.com').first()
        self.assertIsNotNone(usuario)
        # Verificamos que el nuevo usuario pertenezca automáticamente al grupo 'Tutor'
        self.assertTrue(usuario.groups.filter(name='Tutor').exists())

        # Comprobamos que el perfil se haya creado con la cédula y teléfono suministrados
        perfil = UserProfile.objects.filter(user=usuario).first()
        self.assertIsNotNone(perfil)
        self.assertEqual(perfil.id_number, '29999888')
        self.assertEqual(perfil.phone_number, '4249998877')


class AccountsAuditLoggingTests(TestCase):
    """Pruebas para comprobar que los eventos de autenticación se registren en AuditLog."""

    def test_registro_exitoso_genera_evento_de_auditoria(self):
        """El registro exitoso crea una entrada REGISTER_SUCCESS en la bitácora."""
        datos = {
            'full_name': 'Stefany Martínez Auditoría',
            'email': 'stefany.audit@petly.com',
            'phone_prefix': '+58',
            'phone': '4123334455',
            'id_type': 'V',
            'id_number': '30111222',
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        self.client.post(reverse('accounts:register'), datos)

        # Buscamos el usuario y verificamos el evento en la bitácora de auditoría
        usuario = User.objects.filter(email='stefany.audit@petly.com').first()
        evento = AuditLog.objects.filter(action='REGISTER_SUCCESS', user=usuario).first()
        self.assertIsNotNone(evento)
        # Comprobamos que el texto del detalle de auditoría contenga la descripción esperada
        self.assertIn('Registro de nuevo tutor', evento.details)

    def test_inicio_de_sesion_exitoso_genera_auditoria(self):
        """El login correcto genera un evento LOGIN_SUCCESS con el usuario asociado."""
        datos_login = {
            'email': 'edwyn@petly.com',
            'password': '123456789',
        }
        self.client.post(reverse('accounts:login'), datos_login)

        # Verificamos que se haya registrado el evento de inicio de sesión exitoso
        usuario = User.objects.get(username='edwyn')
        evento = AuditLog.objects.filter(action='LOGIN_SUCCESS', user=usuario).first()
        self.assertIsNotNone(evento)
        # Comprobamos que el nombre de usuario figure en los detalles del log
        self.assertIn('edwyn', evento.details)

    def test_inicio_de_sesion_fallido_genera_auditoria(self):
        """Un intento fallido genera un evento LOGIN_FAILED con el correo intentado."""
        datos_erroneos = {
            'email': 'desconocido@petly.com',
            'password': 'ClaveEquivocada',
        }
        self.client.post(reverse('accounts:login'), datos_erroneos)

        # Comprobamos que el fallo quede registrado para trazabilidad y monitoreo de seguridad
        evento = AuditLog.objects.filter(action='LOGIN_FAILED').first()
        self.assertIsNotNone(evento)
        # Verificamos que el correo intentado quede registrado en el log
        self.assertIn('desconocido@petly.com', evento.details)

    def test_cierre_de_sesion_genera_auditoria(self):
        """Cerrar sesión registra un evento LOGOUT para trazabilidad de la sesión."""
        # Forzamos la sesión de Oriana
        usuario = User.objects.get(username='oriana')
        self.client.force_login(usuario)

        # Ejecutamos la petición de cierre de sesión
        self.client.get(reverse('accounts:logout'))

        # Verificamos que el evento LOGOUT se haya registrado en la bitácora
        evento = AuditLog.objects.filter(action='LOGOUT', user=usuario).first()
        self.assertIsNotNone(evento)
