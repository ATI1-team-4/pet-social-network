from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


class PetSpeciesModelTests(TestCase):
    """Pruebas unitarias para el modelo del catálogo PetSpecies."""

    def test_species_creation_and_str(self):
        species = PetSpecies.objects.create(name='Conejo', slug='conejo', icon_name='sparkles')
        self.assertEqual(str(species), 'Conejo')
        self.assertTrue(species.is_active)


class PetModelTests(TestCase):
    """Pruebas unitarias para el modelo Pet y sus propiedades calculadas."""

    def setUp(self):
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
        self.assertEqual(str(self.pet), 'Toby (Perro - Bulldog Francés)')

    def test_pet_gender_properties(self):
        self.assertTrue(self.pet.is_macho)
        self.assertFalse(self.pet.is_hembra)
        self.assertEqual(self.pet.gender, 'M')
        self.assertEqual(self.pet.gender_icon, 'male')
        self.assertEqual(self.pet.gender_label, 'Macho')

        female_pet = Pet(gender=Pet.Gender.HEMBRA)
        self.assertTrue(female_pet.is_hembra)
        self.assertFalse(female_pet.is_macho)
        self.assertEqual(female_pet.gender, 'H')
        self.assertEqual(female_pet.gender_icon, 'female')
        self.assertEqual(female_pet.gender_label, 'Hembra')

    def test_pet_age_calculations(self):
        self.assertGreaterEqual(self.pet.age_years, 2)
        self.assertIn('año', self.pet.age_text)
        self.assertEqual(self.pet.age, self.pet.age_text)

    def test_pet_photo_url_and_media_convention(self):
        self.assertFalse(self.pet.has_photo)
        self.assertEqual(self.pet.photo_url, '/static/images/pets/default_avatar.svg')
        self.assertEqual(self.pet.photo_clean_url, '/static/images/pets/default_avatar.svg')

        self.pet.photo = 'pets/user_1_pet_1_avatar_9f8e7d6c.jpg'
        self.assertTrue(self.pet.has_photo)
        self.assertEqual(
            self.pet.photo_url,
            '/media/pets/user_1_pet_1_avatar_9f8e7d6c.jpg',
        )

    def test_pet_photo_upload_path_convention(self):
        from apps.pets.models import pet_photo_upload_path

        path = pet_photo_upload_path(self.pet, 'avatar.png')
        self.assertTrue(path.startswith(f'pets/user_{self.owner.id}_pet_{self.pet.id}_avatar_'))
        self.assertTrue(path.endswith('.png'))

    def test_pet_temperaments_list(self):
        self.assertEqual(
            self.pet.temperament_list,
            ['Juguetón', 'Sociable', 'Cariñoso'],
        )

    def test_pet_profile_color_hex(self):
        self.assertEqual(self.pet.profile_color_hex, '#FA7D82')

        self.pet.profile_color = Pet.ProfileColor.LILAC
        self.assertEqual(self.pet.profile_color_hex, '#8A4AF3')

        self.pet.profile_color = Pet.ProfileColor.PEACH
        self.assertEqual(self.pet.profile_color_hex, '#FFDAD9')

        self.pet.profile_color = Pet.ProfileColor.MINT
        self.assertEqual(self.pet.profile_color_hex, '#8FFFB4')

    def test_pet_pedigree_flag(self):
        self.assertTrue(self.pet.has_pedigree)

        pet_no_pedigree = Pet(certificate_type='', certificate_number='')
        self.assertFalse(pet_no_pedigree.has_pedigree)

    def test_pet_location_from_owner(self):
        self.assertEqual(self.pet.location, 'Libertador, Distrito Capital')
        self.owner.profile.neighborhood = 'Los Palos Grandes'
        self.owner.profile.municipality = 'Chacao'
        self.owner.profile.state = 'Miranda'
        self.assertEqual(self.pet.location, 'Los Palos Grandes, Chacao, Miranda')


class MatchRequestModelTests(TestCase):
    """Pruebas unitarias para el modelo MatchRequest y sus restricciones de integridad."""

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

    def test_match_request_creation_and_defaults(self):
        req = MatchRequest.objects.create(
            from_pet=self.pet2,
            to_pet=self.pet1,
            notes='Kira está interesada en Toby.',
        )
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)
        self.assertEqual(str(req), 'Kira ➔ Toby (Pendiente)')

    def test_unique_match_request_constraint(self):
        MatchRequest.objects.create(
            from_pet=self.pet2,
            to_pet=self.pet1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MatchRequest.objects.create(
                    from_pet=self.pet2,
                    to_pet=self.pet1,
                )

    def test_prevent_self_match_request_constraint(self):
        with self.assertRaises(IntegrityError):
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
        meetup = PetMeetup.objects.create(
            pet1=self.pet1,
            pet2=self.pet2,
            date=date(2026, 10, 18),
            time=time(11, 0),
            location_name='Parque España (Zona Canina Verificada)',
            status=PetMeetup.MeetupStatus.CONFIRMED,
        )
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.CONFIRMED)
        self.assertIn('Toby', str(meetup))
        self.assertIn('Kira', str(meetup))
        self.assertIn('Confirmado', str(meetup))


class SeedPetsCommandTests(TestCase):
    """Prueba que el comando seed_pets cargue las mascotas y solicitudes esperadas."""

    def test_seed_pets_executes_successfully(self):
        call_command('seed_pets')
        self.assertTrue(Pet.objects.filter(name='Toby').exists())
        self.assertTrue(Pet.objects.filter(name='Luna').exists())
        self.assertTrue(Pet.objects.filter(name='Bella').exists())
        self.assertTrue(Pet.objects.filter(name='Kira').exists())
        self.assertTrue(Pet.objects.filter(name='Maya').exists())
        self.assertTrue(Pet.objects.filter(name='Chloe').exists())
        self.assertTrue(MatchRequest.objects.exists())
        self.assertTrue(PetMeetup.objects.exists())
