from datetime import date

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.accounts.admin import UserProfileAdmin, UserReportAdmin
from apps.accounts.models import UserProfile, UserReport
from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class UserReportAdminTests(TestCase):
    """Pruebas para la interfaz de administración y acciones de moderación de reportes."""

    def setUp(self):
        # Configuramos los desarrolladores Edwyn y Stefany para la prueba del reporte
        self.reporter = User.objects.get(username='edwyn')
        self.offender = User.objects.get(username='stefany')

        # Creamos una especie y mascota asociada al reporte
        species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet = Pet.objects.create(
            owner=self.offender,
            name='Rocky',
            species=species_dog,
            breed='Boxer',
            gender=Pet.Gender.MACHO,
            birth_date=date(2023, 1, 1),
            purpose=Pet.Purpose.BOTH,
        )

        # Registramos el reporte inicial con estado pendiente
        self.report = UserReport.objects.create(
            reported_by=self.reporter,
            reported_user=self.offender,
            reported_pet=self.pet,
            reason='Comportamiento agresivo y perfil falso.',
        )
        self.site = AdminSite()
        self.admin = UserReportAdmin(UserReport, self.site)
        self.factory = RequestFactory()

    def test_accion_suspender_usuario_reportado(self):
        """La acción del panel desactiva la cuenta del usuario infractor y actualiza el reporte."""
        # Comprobamos que la cuenta del usuario esté activa inicialmente
        self.assertTrue(self.offender.is_active)

        # Simulamos la petición del administrador desde el panel
        request = self.factory.get('/admin/accounts/userreport/')
        request.user = self.reporter

        # Capturamos los mensajes enviados por el admin al moderador
        mensajes = []
        self.admin.message_user = lambda req, msg, level: mensajes.append(msg)

        # Ejecutamos la acción personalizada de suspensión
        queryset = UserReport.objects.filter(pk=self.report.pk)
        self.admin.ban_reported_user(request, queryset)

        # Recargamos desde la base de datos para comprobar los cambios
        self.offender.refresh_from_db()
        self.report.refresh_from_db()

        # Verificamos que la cuenta haya sido desactivada (is_active=False)
        self.assertFalse(self.offender.is_active)
        # Comprobamos que el reporte se marque con estado de acción tomada
        self.assertEqual(self.report.status, UserReport.ReportStatus.ACTION_TAKEN)
        # Verificamos que se haya generado un mensaje de confirmación
        self.assertTrue(len(mensajes) > 0)
        self.assertIn('suspendidos', mensajes[0].lower())

    def test_configuracion_columnas_y_filtros_admin(self):
        """Verifica que el admin exponga los campos clave en su lista de visualización."""
        # Verificamos las columnas mostradas en el listado de reportes
        self.assertIn('reported_user', self.admin.list_display)
        self.assertIn('reported_by', self.admin.list_display)
        self.assertIn('status', self.admin.list_display)
        # Comprobamos que exista filtro lateral por estado
        self.assertIn('status', self.admin.list_filter)


class UserProfileAdminTests(TestCase):
    """Pruebas de visualización del perfil de usuario en el panel administrativo."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = UserProfileAdmin(UserProfile, self.site)

    def test_columnas_list_display_perfil(self):
        """El listado de perfiles debe mostrar ubicación y métricas del tutor."""
        # Verificamos que las columnas de usuario, municipio y calificación aparezcan en el panel
        self.assertIn('user', self.admin.list_display)
        self.assertIn('municipality', self.admin.list_display)
        self.assertIn('get_rating', self.admin.list_display)
