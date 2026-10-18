from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.accounts.admin import CustomUserAdmin
from apps.pets.admin import MatchRequestAdmin, PetAdmin, PetMeetupAdmin, PetSpeciesAdmin
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


class PetsAdminTests(TestCase):
    """Pruebas unitarias para la configuración del Django Admin en la app pets."""

    def setUp(self):
        self.site = AdminSite()
        self.user = User.objects.get(username='admin')
        self.factory = RequestFactory()
        self.species_admin = PetSpeciesAdmin(PetSpecies, self.site)
        self.pet_admin = PetAdmin(Pet, self.site)
        self.match_admin = MatchRequestAdmin(MatchRequest, self.site)
        self.meetup_admin = PetMeetupAdmin(PetMeetup, self.site)
        self.custom_user_admin = CustomUserAdmin(User, self.site)

        self.species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Toby',
            species=self.species_dog,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date=date(2022, 4, 15),
            weight_kg=Decimal('12.50'),
            purpose=Pet.Purpose.BOTH,
        )

    def test_pet_admin_list_display_and_search(self):
        """Verifica que el admin de mascotas muestre nombre, tutor y permita buscar por raza."""
        # Verificamos que el nombre y el tutor aparezcan en las columnas del listado admin
        self.assertIn('name', self.pet_admin.list_display)
        self.assertIn('owner', self.pet_admin.list_display)
        # Comprobamos que el campo is_active_for_match sea editable directamente desde el listado
        self.assertIn('is_active_for_match', self.pet_admin.list_editable)
        # Verificamos que se pueda buscar mascotas por raza en la barra de búsqueda
        self.assertIn('breed', self.pet_admin.search_fields)

    def test_match_request_admin_configuration(self):
        """Verifica que las solicitudes de match muestren las mascotas y filtren por estado."""
        # Verificamos que el listado muestre la mascota emisora y la receptora
        self.assertIn('from_pet', self.match_admin.list_display)
        self.assertIn('to_pet', self.match_admin.list_display)
        # Comprobamos que el panel incluya un filtro lateral por estado de la solicitud
        self.assertIn('status', self.match_admin.list_filter)

    def test_pet_meetup_admin_configuration(self):
        """Verifica que los encuentros muestren anfitrión, invitado y lugar pactado."""
        # Verificamos las columnas principales del listado de encuentros
        self.assertIn('host_pet', self.meetup_admin.list_display)
        self.assertIn('guest_pet', self.meetup_admin.list_display)
        self.assertIn('location_name', self.meetup_admin.list_display)
        # Comprobamos que exista filtro lateral por fecha del encuentro
        self.assertIn('date', self.meetup_admin.list_filter)

    def test_custom_user_admin_displays_city_and_rating(self):
        """Verifica los métodos auxiliares de ciudad y calificación en el admin de usuarios."""
        city = self.custom_user_admin.get_city(self.user)
        rating = self.custom_user_admin.get_rating(self.user)
        # Comprobamos que los métodos del admin retornen los valores exactos del perfil del usuario
        self.assertEqual(city, self.user.profile.city)
        self.assertEqual(rating, self.user.profile.rating)
