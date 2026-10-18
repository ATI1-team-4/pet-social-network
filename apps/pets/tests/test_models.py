from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


class PetSpeciesModelTests(TestCase):
    """Pruebas unitarias para el modelo del catálogo PetSpecies."""

    def test_species_creation_and_str(self):
        """Verifica la creación y representación en cadena del catálogo de especies."""
        species = PetSpecies.objects.create(name='Conejo', slug='conejo', icon_name='sparkles')
        # Comprobamos que la representación en cadena (__str__) devuelva el nombre de la especie
        self.assertEqual(str(species), 'Conejo')
        # Verificamos que por defecto la especie se cree en estado activo
        self.assertTrue(species.is_active)


class PetModelTests(TestCase):
    """Pruebas unitarias para el modelo Pet y sus propiedades calculadas."""

    def setUp(self):
        # Obtenemos al desarrollador Edwyn Guzmán como tutor
        self.owner = User.objects.get(username='edwyn')
        self.species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet = Pet.objects.create(
            owner=self.owner,
            name='Toby',
            species=self.species_dog,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 4, 15),
            weight_kg=Decimal('12.50'),
            description='Bulldog juguetón y sociable.',
            certificate_type='Certificado FCI',
            certificate_number='FCI-VE-10294',
            purpose=Pet.Purpose.BOTH,
            is_active_for_match=True,
            max_search_distance_km=15,
            temperaments='Juguetón, Sociable, Cariñoso',
            profile_color=Pet.ProfileColor.CORAL,
        )

    def test_pet_str_representation(self):
        """La representación en texto debe incluir nombre, especie y raza."""
        # Comprobamos el formato de la representación en texto del modelo
        self.assertEqual(str(self.pet), 'Toby (Perro - Bulldog Francés)')

    def test_pet_gender_properties(self):
        """Comprueba las propiedades auxiliares de género (is_macho, is_hembra, etiquetas e íconos)."""
        # Evaluamos para mascota macho
        self.assertTrue(self.pet.is_macho)
        self.assertFalse(self.pet.is_hembra)
        self.assertEqual(self.pet.gender, 'M')
        self.assertEqual(self.pet.gender_icon, 'male')
        self.assertEqual(self.pet.gender_label, 'Macho')

        # Evaluamos para mascota hembra
        female_pet = Pet(gender=Pet.Gender.HEMBRA)
        self.assertTrue(female_pet.is_hembra)
        self.assertFalse(female_pet.is_macho)
        self.assertEqual(female_pet.gender, 'H')
        self.assertEqual(female_pet.gender_icon, 'female')
        self.assertEqual(female_pet.gender_label, 'Hembra')

    def test_pet_age_calculations(self):
        """Calcula la edad en años y el texto legible a partir de la fecha de nacimiento."""
        # Comprobamos que el cálculo de edad sea mayor o igual a 2 años
        self.assertGreaterEqual(self.pet.age_years, 2)
        # Verificamos que la palabra 'año' forme parte del texto descriptivo de la edad
        self.assertIn('año', self.pet.age_text)
        self.assertEqual(self.pet.age, self.pet.age_text)

    def test_pet_photo_url_and_media_convention(self):
        """Devuelve el avatar por defecto si no tiene foto, o la ruta de media si fue cargada."""
        # Sin foto asignada debe devolver la ilustración por defecto en static
        self.assertFalse(self.pet.has_photo)
        self.assertEqual(self.pet.photo_url, '/static/images/pets/default_avatar.svg')
        self.assertEqual(self.pet.photo_clean_url, '/static/images/pets/default_avatar.svg')

        # Asignando un archivo en la carpeta de media
        self.pet.photo = 'pets/user_1_pet_1_avatar_9f8e7d6c.jpg'
        self.assertTrue(self.pet.has_photo)
        self.assertEqual(
            self.pet.photo_url,
            '/media/pets/user_1_pet_1_avatar_9f8e7d6c.jpg',
        )

    def test_pet_photo_upload_path_convention(self):
        """Genera el nombre del archivo siguiendo el estándar de tutor y mascota."""
        from apps.pets.models import pet_photo_upload_path

        path = pet_photo_upload_path(self.pet, 'avatar.png')
        # Verificamos que el prefijo del archivo contenga los IDs del tutor y de la mascota
        self.assertTrue(path.startswith(f'pets/user_{self.owner.id}_pet_{self.pet.id}_avatar_'))
        self.assertTrue(path.endswith('.png'))

    def test_pet_temperaments_list(self):
        """Convierte la cadena separada por comas en una lista de temperamentos limpia."""
        # Comprobamos que el texto se transforme en una lista de strings limpios
        self.assertEqual(
            self.pet.temperament_list,
            ['Juguetón', 'Sociable', 'Cariñoso'],
        )

    def test_pet_profile_color_hex(self):
        """Mapea cada opción de color a su código hexadecimal correspondiente para la interfaz."""
        # Color coral por defecto
        self.assertEqual(self.pet.profile_color_hex, '#FA7D82')

        # Color lila
        self.pet.profile_color = Pet.ProfileColor.LILAC
        self.assertEqual(self.pet.profile_color_hex, '#8A4AF3')

        # Color durazno
        self.pet.profile_color = Pet.ProfileColor.PEACH
        self.assertEqual(self.pet.profile_color_hex, '#FFDAD9')

        # Color menta
        self.pet.profile_color = Pet.ProfileColor.MINT
        self.assertEqual(self.pet.profile_color_hex, '#8FFFB4')

    def test_pet_pedigree_flag(self):
        """Determina si la mascota cuenta con certificación de pedigrí registrada."""
        # Toby tiene certificado FCI registrado
        self.assertTrue(self.pet.has_pedigree)

        # Mascota sin certificados registrados
        pet_no_pedigree = Pet(certificate_type='', certificate_number='')
        self.assertFalse(pet_no_pedigree.has_pedigree)

    def test_pet_location_from_owner(self):
        """Obtiene la ubicación formateada a partir del perfil del tutor responsable."""
        # Ubicación inicial por defecto de Edwyn
        self.assertEqual(self.pet.location, 'Libertador, Distrito Capital')

        # Actualizamos datos geográficos en el perfil del tutor
        self.owner.profile.neighborhood = 'Los Palos Grandes'
        self.owner.profile.municipality = 'Chacao'
        self.owner.profile.state = 'Miranda'
        # Comprobamos que la propiedad location de la mascota refleje los nuevos datos
        self.assertEqual(self.pet.location, 'Los Palos Grandes, Chacao, Miranda')


class MatchRequestModelTests(TestCase):
    """Pruebas unitarias para el modelo MatchRequest y sus restricciones de integridad."""

    def setUp(self):
        # Obtenemos los desarrolladores Edwyn y Stefany como tutores
        self.user1 = User.objects.get(username='edwyn')
        self.user2 = User.objects.get(username='stefany')
        self.species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet1 = Pet.objects.create(
            owner=self.user1,
            name='Toby',
            species=self.species_dog,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 4, 15),
            purpose=Pet.Purpose.BOTH,
        )
        self.pet2 = Pet.objects.create(
            owner=self.user2,
            name='Kira',
            species=self.species_dog,
            breed='Pomerania Mini',
            gender=Pet.Gender.HEMBRA,
            birth_date=date(2023, 6, 15),
            purpose=Pet.Purpose.MATING,
        )

    def test_match_request_creation_and_defaults(self):
        """Verifica la creación de una solicitud de match con estado inicial pendiente."""
        req = MatchRequest.objects.create(
            from_pet=self.pet2,
            to_pet=self.pet1,
            notes='Kira está interesada en Toby.',
        )
        # Comprobamos que el estado por defecto sea PENDING
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)
        # Verificamos la representación en texto del modelo
        self.assertEqual(str(req), 'Kira ➔ Toby (Pendiente)')

    def test_unique_match_request_constraint(self):
        """Verifica que la base de datos impida registrar dos solicitudes idénticas entre las mismas mascotas."""
        MatchRequest.objects.create(
            from_pet=self.pet2,
            to_pet=self.pet1,
        )
        # Comprobamos que se lance IntegrityError por violación de unicidad al repetir la solicitud
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MatchRequest.objects.create(
                    from_pet=self.pet2,
                    to_pet=self.pet1,
                )

    def test_prevent_self_match_request_constraint(self):
        """Verifica que una mascota no pueda enviarse una solicitud de match a sí misma."""
        # Comprobamos que la base de datos o el modelo rechacen una solicitud dirigida a la misma mascota
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                MatchRequest.objects.create(
                    from_pet=self.pet1,
                    to_pet=self.pet1,
                )


class PetMeetupModelTests(TestCase):
    """Pruebas unitarias para el modelo PetMeetup."""

    def setUp(self):
        self.user1 = User.objects.get(username='edwyn')
        self.user2 = User.objects.get(username='stefany')
        self.species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet1 = Pet.objects.create(
            owner=self.user1,
            name='Toby',
            species=self.species_dog,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 4, 15),
            purpose=Pet.Purpose.BOTH,
        )
        self.pet2 = Pet.objects.create(
            owner=self.user2,
            name='Kira',
            species=self.species_dog,
            breed='Pomerania Mini',
            gender=Pet.Gender.HEMBRA,
            birth_date=date(2023, 6, 15),
            purpose=Pet.Purpose.MATING,
        )

    def test_pet_meetup_creation_and_str(self):
        """Verifica la persistencia de una cita y su representación en texto."""
        meetup = PetMeetup.objects.create(
            host_pet=self.pet1,
            guest_pet=self.pet2,
            date=date(2026, 10, 18),
            time=time(11, 0),
            location_name='Parque España (Zona Canina Verificada)',
            status=PetMeetup.MeetupStatus.CONFIRMED,
        )
        # Comprobamos el estado del encuentro y el usuario que lo agendó
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.CONFIRMED)
        self.assertEqual(meetup.scheduled_by, self.user1)
        # Verificamos que los nombres de ambas mascotas y el estado figuren en el texto
        self.assertIn('Toby', str(meetup))
        self.assertIn('Kira', str(meetup))
        self.assertIn('Confirmado', str(meetup))


class SeedPetsCommandTests(TestCase):
    """Prueba que el comando seed_pets cargue las mascotas y solicitudes esperadas."""

    def test_seed_pets_executes_successfully(self):
        """Verifica la ejecución del comando seed_pets sin errores y la existencia de los datos."""
        call_command('seed_pets')
        # Verificamos que las mascotas del semillero inicial existan en la base de datos
        self.assertTrue(Pet.objects.filter(name='Toby').exists())
        self.assertTrue(Pet.objects.filter(name='Luna').exists())
        self.assertTrue(Pet.objects.filter(name='Bella').exists())
        self.assertTrue(Pet.objects.filter(name='Kira').exists())
        self.assertTrue(Pet.objects.filter(name='Maya').exists())
        self.assertTrue(Pet.objects.filter(name='Chloe').exists())
        # Comprobamos que se hayan generado solicitudes de match y encuentros
        self.assertTrue(MatchRequest.objects.exists())
        self.assertTrue(PetMeetup.objects.exists())
