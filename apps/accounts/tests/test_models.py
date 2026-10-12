from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.accounts.admin import UserReportAdmin
from apps.accounts.models import UserReport
from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class MockRequest:
    pass


class UserProfileModelTests(TestCase):
    """Pruebas unitarias para los atributos y comportamiento del modelo UserProfile."""

    def setUp(self):
        self.user = User.objects.get(username='edwyn')
        self.profile = self.user.profile

    def test_user_profile_default_values(self):
        """Verifica los valores por defecto configurados en UserProfile."""
        self.assertEqual(self.profile.state, 'Distrito Capital')
        self.assertEqual(self.profile.municipality, 'Libertador')
        self.assertEqual(self.profile.neighborhood, '')
        self.assertEqual(self.profile.city, 'Libertador')
        self.assertEqual(self.profile.rating, Decimal('5.00'))
        self.assertEqual(self.profile.completed_meetings_count, 0)
        self.assertIsNone(self.profile.latitude)
        self.assertIsNone(self.profile.longitude)

    def test_user_profile_extended_fields(self):
        """Verifica la asignación y persistencia de campos de ubicación estructurada, fecha y afinidades."""
        self.profile.state = 'Miranda'
        self.profile.municipality = 'Guaicaipuro'
        self.profile.neighborhood = 'Los Teques'
        self.profile.latitude = 10.3456
        self.profile.longitude = -67.0421
        self.profile.birth_date = date(1998, 5, 20)
        self.profile.gender = 'M'
        self.profile.favorite_color = 'Coral'
        self.profile.favorite_book = 'Clean Architecture'
        self.profile.favorite_music = 'Rock'
        self.profile.favorite_videogame = 'Zelda'
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.state, 'Miranda')
        self.assertEqual(self.profile.municipality, 'Guaicaipuro')
        self.assertEqual(self.profile.neighborhood, 'Los Teques')
        self.assertEqual(self.profile.city, 'Guaicaipuro')
        self.assertEqual(self.profile.location_display, 'Los Teques, Guaicaipuro, Miranda')
        self.assertAlmostEqual(self.profile.latitude, 10.3456)
        self.assertAlmostEqual(self.profile.longitude, -67.0421)
        self.assertEqual(self.profile.birth_date, date(1998, 5, 20))
        self.assertEqual(self.profile.gender, 'M')
        self.assertEqual(self.profile.rating, Decimal('5.00'))
        self.assertEqual(self.profile.completed_meetings_count, 0)
        self.assertEqual(self.profile.favorite_color, 'Coral')
        self.assertEqual(self.profile.favorite_book, 'Clean Architecture')
        self.assertEqual(self.profile.favorite_music, 'Rock')
        self.assertEqual(self.profile.favorite_videogame, 'Zelda')

    def test_user_profile_str_representation(self):
        """Verifica la representación en cadena del perfil."""
        full_name = self.user.get_full_name()
        expected = f'Perfil de {full_name}'
        self.assertEqual(str(self.profile), expected)

    def test_user_profile_avatar_url_and_fallback(self):
        """Verifica que el avatar por defecto devuelva el SVG neutro estilo WhatsApp."""
        self.assertFalse(self.profile.has_avatar)
        self.assertEqual(self.profile.avatar_url, '/static/images/avatars/default_user.svg')

        self.profile.avatar = 'avatars/user_1_avatar_9f8e7d6c.jpg'
        self.assertTrue(self.profile.has_avatar)
        self.assertEqual(
            self.profile.avatar_url,
            '/media/avatars/user_1_avatar_9f8e7d6c.jpg',
        )

    def test_user_avatar_upload_path_convention(self):
        """Verifica que la ruta generada para el avatar siga la convención definida."""
        from apps.accounts.models import user_avatar_upload_path

        path = user_avatar_upload_path(self.profile, 'perfil.jpg')
        self.assertTrue(path.startswith(f'avatars/user_{self.user.id}_avatar_'))
        self.assertTrue(path.endswith('.jpg'))


class UserReportModelAndAdminTests(TestCase):
    """Pruebas unitarias para el modelo UserReport y la acción de moderación en Admin."""

    def setUp(self):
        self.reporter = User.objects.get(username='edwyn')
        self.offender = User.objects.get(username='stefany')
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
        self.report = UserReport.objects.create(
            reported_by=self.reporter,
            reported_user=self.offender,
            reported_pet=self.pet,
            reason='Comportamiento agresivo y perfil falso.',
        )
        self.site = AdminSite()
        self.admin = UserReportAdmin(UserReport, self.site)
        self.factory = RequestFactory()

    def test_user_report_creation_and_defaults(self):
        """Verifica la creación del reporte con estado inicial PENDING."""
        self.assertEqual(self.report.status, UserReport.ReportStatus.PENDING)
        self.assertEqual(self.report.reported_by, self.reporter)
        self.assertEqual(self.report.reported_user, self.offender)
        self.assertEqual(self.report.reported_pet, self.pet)
        self.assertIn('Rocky', str(self.report.reported_pet))
        self.assertIn(str(self.report.pk), str(self.report))

    def test_ban_reported_user_admin_action(self):
        """Verifica que la acción del panel suspenda al usuario y actualice el reporte."""
        self.assertTrue(self.offender.is_active)

        request = self.factory.get('/admin/accounts/userreport/')
        request.user = self.reporter
        # Mock message_user
        messages_sent = []
        self.admin.message_user = lambda req, msg, level: messages_sent.append(msg)

        queryset = UserReport.objects.filter(pk=self.report.pk)
        self.admin.ban_reported_user(request, queryset)

        self.offender.refresh_from_db()
        self.report.refresh_from_db()

        self.assertFalse(self.offender.is_active)
        self.assertEqual(self.report.status, UserReport.ReportStatus.ACTION_TAKEN)
        self.assertTrue(len(messages_sent) > 0)
        self.assertIn('suspendidos', messages_sent[0].lower())
