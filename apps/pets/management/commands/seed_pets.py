from datetime import date, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga mascotas de prueba, solicitudes de match y citas de socialización'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE('Iniciando carga de datos semilla para el módulo de match...')
        )

        # Catálogo oficial de especies
        species_catalog = [
            {'name': 'Perro', 'slug': 'perro', 'icon_name': 'dog'},
            {'name': 'Gato', 'slug': 'gato', 'icon_name': 'paw'},
            {'name': 'Conejo', 'slug': 'conejo', 'icon_name': 'sparkles'},
            {'name': 'Hurón', 'slug': 'huron', 'icon_name': 'sparkles'},
            {'name': 'Otro', 'slug': 'otro', 'icon_name': 'sparkles'},
        ]
        species_objs = {}
        for sp_data in species_catalog:
            sp_obj, _ = PetSpecies.objects.update_or_create(
                slug=sp_data['slug'],
                defaults=sp_data,
            )
            species_objs[sp_data['slug']] = sp_obj
            species_objs[sp_data['name']] = sp_obj
        dog_species = species_objs['perro']

        # Actualizar perfiles de usuarios de prueba con datos para match
        user_profiles_data = {
            'admin': {
                'city': 'Caracas',
                'rating': Decimal('5.00'),
                'completed_meetings_count': 15,
                'favorite_color': 'Coral',
                'favorite_book': 'El principito',
                'favorite_music': 'Rock clásico',
                'favorite_videogame': 'Super Mario',
                'gender': 'M',
            },
            'edwyn': {
                'city': 'Caracas',
                'rating': Decimal('5.00'),
                'completed_meetings_count': 10,
                'favorite_color': 'Azul',
                'favorite_book': 'Clean Code',
                'favorite_music': 'Synthwave',
                'favorite_videogame': 'The Witcher',
                'gender': 'M',
            },
            'sofia': {
                'city': 'Los Teques',
                'rating': Decimal('5.00'),
                'completed_meetings_count': 18,
                'favorite_color': 'Coral',
                'favorite_book': 'Harry Potter',
                'favorite_music': 'Indie Rock',
                'favorite_videogame': 'Animal Crossing',
                'gender': 'F',
            },
            'maria': {
                'city': 'Caracas',
                'rating': Decimal('4.90'),
                'completed_meetings_count': 12,
                'favorite_color': 'Lila',
                'favorite_book': 'Cien años de soledad',
                'favorite_music': 'Pop',
                'favorite_videogame': 'The Sims',
                'gender': 'F',
            },
            'bryan': {
                'city': 'El Hatillo',
                'rating': Decimal('4.80'),
                'completed_meetings_count': 9,
                'favorite_color': 'Menta',
                'favorite_book': 'Dune',
                'favorite_music': 'Electrónica',
                'favorite_videogame': 'Zelda: Breath of the Wild',
                'gender': 'M',
            },
            'oriana': {
                'city': 'Caracas',
                'rating': Decimal('4.95'),
                'completed_meetings_count': 8,
                'favorite_color': 'Melocotón',
                'favorite_book': 'El Hobbit',
                'favorite_music': 'R&B',
                'favorite_videogame': 'Pokemon',
                'gender': 'F',
            },
        }

        for username, p_data in user_profiles_data.items():
            user = User.objects.filter(username=username).first()
            if user:
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults=p_data,
                )

        admin_user = User.objects.filter(username='admin').first() or User.objects.first()
        sofia_user = User.objects.filter(username='sofia').first() or admin_user
        maria_user = User.objects.filter(username='maria').first() or admin_user
        bryan_user = User.objects.filter(username='bryan').first() or admin_user
        oriana_user = User.objects.filter(username='oriana').first() or admin_user

        # Mascotas oficiales de la plataforma
        pets_spec = [
            {
                'owner': admin_user,
                'name': 'Toby',
                'species': dog_species,
                'breed': 'Bulldog Francés',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 4, 15),
                'weight_kg': Decimal('12.50'),
                'certificate_type': 'Certificado FCI / con pedigrí',
                'certificate_number': 'FCI-VE-10294',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 10,
                'temperaments': 'Juguetón, Sociable, Cariñoso',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': (
                    'Adora correr en el parque, jugar con pelotas y dormir siestas al sol. '
                    'Muy amigable con otros perros.'
                ),
            },
            {
                'owner': admin_user,
                'name': 'Luna',
                'species': dog_species,
                'breed': 'Golden Retriever',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2021, 6, 20),
                'weight_kg': Decimal('28.00'),
                'certificate_type': 'Pedigrí certificado',
                'certificate_number': 'FCI-VE-77401',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': False,
                'max_search_distance_km': 15,
                'temperaments': 'Tranquilo, Cariñoso, Curioso',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Le encanta nadar, buscar pelotas en el parque y descansar en familia.',
            },
            {
                'owner': sofia_user,
                'name': 'Bella',
                'species': dog_species,
                'breed': 'Pastor Australiano',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2022, 10, 12),
                'weight_kg': Decimal('21.40'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-MX-88421',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 25,
                'temperaments': 'Juguetona, Sociable, Cariñosa, Ágil',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': (
                    'Bella es una perrita alegre, noble y muy inteligente. Adora correr al aire libre, '
                    'resolver acertijos de olfato y convivir tranquilamente con niños y otros caninos.'
                ),
            },
            {
                'owner': maria_user,
                'name': 'Kira',
                'species': dog_species,
                'breed': 'Pomerania Mini',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 6, 15),
                'weight_kg': Decimal('3.20'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-11029',
                'purpose': Pet.Purpose.MATING,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Tranquila, Cariñosa, Sociable',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': (
                    'Kira es súper dócil, tierna y juguetona en calma. Buscamos una cruza ética '
                    'certificada con contrato de seguimiento mutuo.'
                ),
            },
            {
                'owner': bryan_user,
                'name': 'Maya',
                'species': dog_species,
                'breed': 'Boston Terrier',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2022, 1, 8),
                'weight_kg': Decimal('7.80'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-99412',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Curiosa, Juguetona, Protectora',
                'profile_color': Pet.ProfileColor.MINT,
                'description': (
                    'Maya es activa, adora los paseos largos por el parque y jugar con pelotas. '
                    'Muy cariñosa con la familia y otros compañeros caninos.'
                ),
            },
            {
                'owner': oriana_user,
                'name': 'Chloe',
                'species': dog_species,
                'breed': 'Bulldog Francés',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2024, 2, 10),
                'weight_kg': Decimal('10.20'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-55219',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 10,
                'temperaments': 'Juguetona, Cariñosa',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Chloe es vivaz, le encanta convivir con otros perritos y hacer nuevos amigos.',
            },
        ]

        created_pets = {}
        for spec in pets_spec:
            pet_defaults = {**spec, 'photo': None}
            pet, created = Pet.objects.update_or_create(
                owner=spec['owner'],
                name=spec['name'],
                defaults=pet_defaults,
            )
            created_pets[spec['name']] = pet

            status = 'creada' if created else 'actualizada'
            self.stdout.write(f'  • Mascota {pet.name} ({status})')

        # Solicitudes de match (Interesadas en Toby)
        toby = created_pets.get('Toby')
        kira = created_pets.get('Kira')
        bella = created_pets.get('Bella')
        chloe = created_pets.get('Chloe')
        maya = created_pets.get('Maya')

        if toby and kira:
            req_kira, _ = MatchRequest.objects.update_or_create(
                from_pet=kira,
                to_pet=toby,
                defaults={
                    'status': MatchRequest.RequestStatus.ACCEPTED,
                    'notes': (
                        '¡Hola Sofía! Nos encantó Toby. Kira es súper dócil, tierna y juguetona en calma. '
                        'Buscamos una cruza ética certificada para fin de año con contrato de seguimiento mutuo.'
                    ),
                },
            )
            # Cita confirmada entre Toby y Kira
            PetMeetup.objects.update_or_create(
                pet1=toby,
                pet2=kira,
                date=date(2026, 10, 18),
                defaults={
                    'match_request': req_kira,
                    'time': time(11, 0),
                    'location_name': 'Parque España (Zona Canina Verificada)',
                    'status': PetMeetup.MeetupStatus.CONFIRMED,
                    'notes': 'Encuentro inicial de socialización canina supervisado en espacio cercado.',
                },
            )

        if toby and chloe:
            MatchRequest.objects.update_or_create(
                from_pet=chloe,
                to_pet=toby,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Chloe busca amigos de su misma raza para tardes de juego.',
                },
            )

        if toby and maya:
            MatchRequest.objects.update_or_create(
                from_pet=maya,
                to_pet=toby,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Maya busca compañeros activos para socialización.',
                },
            )

        if toby and bella:
            MatchRequest.objects.update_or_create(
                from_pet=bella,
                to_pet=toby,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Bella busca citas de socialización y compatibilidad.',
                },
            )

        self.stdout.write(
            self.style.SUCCESS('¡Semilla de mascotas y match completada exitosamente!')
        )
