from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import UserReport
from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class UserProfileModelTests(TestCase):
    """Pruebas unitarias para los atributos y comportamiento del modelo UserProfile."""

    def setUp(self):
        self.user = User.objects.get(username='edwyn')
        self.profile = self.user.profile

    def test_user_profile_default_values(self):
        """Verifica los valores por defecto configurados en UserProfile."""
        # Comprobamos los valores de ubicación iniciales en Distrito Capital
        self.assertEqual(self.profile.state, 'Distrito Capital')
        self.assertEqual(self.profile.municipality, 'Libertador')
        self.assertEqual(self.profile.neighborhood, '')
        self.assertEqual(self.profile.city, 'Libertador')
        # Comprobamos la reputación inicial de 5 estrellas
        self.assertEqual(self.profile.rating, Decimal('5.00'))
        self.assertEqual(self.profile.completed_meetings_count, 0)
        # Verificamos que las coordenadas GPS comiencen sin valor (None)
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
        # Verificamos la persistencia de los datos extendidos en la base de datos
        self.assertEqual(self.profile.state, 'Miranda')
        self.assertEqual(self.profile.municipality, 'Guaicaipuro')
        self.assertEqual(self.profile.neighborhood, 'Los Teques')
        self.assertEqual(self.profile.city, 'Guaicaipuro')
        self.assertEqual(self.profile.location_display, 'Los Teques, Guaicaipuro, Miranda')
        self.assertAlmostEqual(self.profile.latitude, 10.3456)
        self.assertAlmostEqual(self.profile.longitude, -67.0421)
        self.assertEqual(self.profile.birth_date, date(1998, 5, 20))
        self.assertEqual(self.profile.gender, 'M')
        self.assertEqual(self.profile.favorite_color, 'Coral')
        self.assertEqual(self.profile.favorite_book, 'Clean Architecture')
        self.assertEqual(self.profile.favorite_music, 'Rock')
        self.assertEqual(self.profile.favorite_videogame, 'Zelda')

    def test_user_profile_str_representation(self):
        """Verifica la representación en cadena del perfil."""
        full_name = self.user.get_full_name()
        expected = f'Perfil de {full_name}'
        # Comprobamos que el método __str__ devuelva el nombre completo del tutor
        self.assertEqual(str(self.profile), expected)

    def test_user_profile_avatar_url_and_fallback(self):
        """Verifica que el avatar por defecto devuelva el SVG neutro estilo WhatsApp."""
        from unittest.mock import patch

        # Sin avatar configurado debe indicar has_avatar en False y ruta de static
        self.assertFalse(self.profile.has_avatar)
        self.assertEqual(self.profile.avatar_url, '/static/images/avatars/default_user.svg')

        # Con archivo existente en el almacenamiento
        self.profile.avatar = 'avatars/user_1_avatar_9f8e7d6c.jpg'
        with patch.object(self.profile.avatar.storage, 'exists', return_value=True):
            self.assertTrue(self.profile.has_avatar)
            self.assertEqual(
                self.profile.avatar_url,
                '/media/avatars/user_1_avatar_9f8e7d6c.jpg',
            )

        # Con ruta configurada pero archivo físico inexistente
        with patch.object(self.profile.avatar.storage, 'exists', return_value=False):
            self.assertFalse(self.profile.has_avatar)
            self.assertEqual(
                self.profile.avatar_url,
                '/static/images/avatars/default_user.svg',
            )

    def test_user_avatar_upload_path_convention(self):
        """Verifica que la ruta generada para el avatar siga la convención definida."""
        from apps.accounts.models import user_avatar_upload_path

        path = user_avatar_upload_path(self.profile, 'perfil.jpg')
        # Verificamos que la ruta incluya el ID del usuario en el directorio avatars
        self.assertTrue(path.startswith(f'avatars/user_{self.user.id}_avatar_'))
        self.assertTrue(path.endswith('.jpg'))


class UserReportModelTests(TestCase):
    """Pruebas unitarias para el modelo UserReport."""

    def setUp(self):
        # Configuramos los desarrolladores Edwyn (denunciante) y Stefany (denunciada)
        self.reporter = User.objects.get(username='edwyn')
        self.offender = User.objects.get(username='stefany')

        # Creamos una mascota perteneciente al usuario reportado
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

        # Creamos el reporte de prueba
        self.report = UserReport.objects.create(
            reported_by=self.reporter,
            reported_user=self.offender,
            reported_pet=self.pet,
            reason='Comportamiento agresivo y perfil falso.',
        )

    def test_creacion_y_valores_por_defecto_del_reporte(self):
        """El reporte debe inicializarse con estado PENDING y relacionar a los usuarios."""
        # Comprobamos el estado inicial en PENDING
        self.assertEqual(self.report.status, UserReport.ReportStatus.PENDING)
        self.assertEqual(self.report.reported_by, self.reporter)
        self.assertEqual(self.report.reported_user, self.offender)
        self.assertEqual(self.report.reported_pet, self.pet)
        # Verificamos que el nombre de la mascota y el ID figuren en la representación en cadena
        self.assertIn('Rocky', str(self.report.reported_pet))
        self.assertIn(str(self.report.pk), str(self.report))

    def test_estados_posibles_del_reporte(self):
        """Verifica que el reporte permita transiciones entre sus diferentes estados."""
        self.report.status = UserReport.ReportStatus.ACTION_TAKEN
        self.report.save()
        self.report.refresh_from_db()
        # Comprobamos que el cambio de estado se mantenga en la base de datos
        self.assertEqual(self.report.status, UserReport.ReportStatus.ACTION_TAKEN)
