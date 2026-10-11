from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile, UserReport
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga mascotas de prueba, solicitudes de match y citas de socialización con datos diversos y equilibrados'

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
        cat_species = species_objs['gato']

        # Actualizar perfiles de todos los usuarios de desarrollo con datos para match
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
                'completed_meetings_count': 12,
                'favorite_color': 'Azul',
                'favorite_book': 'Clean Code',
                'favorite_music': 'Synthwave',
                'favorite_videogame': 'The Witcher',
                'gender': 'M',
            },
            'stefany': {
                'city': 'Caracas',
                'rating': Decimal('4.95'),
                'completed_meetings_count': 8,
                'favorite_color': 'Rosa',
                'favorite_book': 'Orgullo y prejuicio',
                'favorite_music': 'Indie Pop',
                'favorite_videogame': 'Stardew Valley',
                'gender': 'F',
            },
            'tutor': {
                'city': 'San Antonio de Los Altos',
                'rating': Decimal('4.85'),
                'completed_meetings_count': 6,
                'favorite_color': 'Verde',
                'favorite_book': 'Sapiens',
                'favorite_music': 'Acústica',
                'favorite_videogame': 'Minecraft',
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
        edwyn_user = User.objects.filter(username='edwyn').first() or admin_user
        stefany_user = User.objects.filter(username='stefany').first() or admin_user
        tutor_user = User.objects.filter(username='tutor').first() or admin_user
        sofia_user = User.objects.filter(username='sofia').first() or admin_user
        maria_user = User.objects.filter(username='maria').first() or admin_user
        bryan_user = User.objects.filter(username='bryan').first() or admin_user
        oriana_user = User.objects.filter(username='oriana').first() or admin_user

        # Mascotas de la plataforma (equilibradas entre machos y hembras, con perros y gatos)
        pets_spec = [
            # 1. Mascotas de Admin
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
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Tranquilo, Cariñoso, Curioso',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Le encanta nadar, buscar pelotas en el parque y descansar en familia.',
            },
            # 2. Mascotas de Edwyn (usuario desarrollador principal)
            {
                'owner': edwyn_user,
                'name': 'Simba',
                'species': dog_species,
                'breed': 'Golden Retriever',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 5, 10),
                'weight_kg': Decimal('31.20'),
                'certificate_type': 'Certificado FCI / con pedigrí',
                'certificate_number': 'FCI-VE-88301',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Juguetón, Noble, Cariñoso, Sociable',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': 'Simba es un Golden amigable y enérgico, perfecto para socializar y jugar en parques verdes.',
            },
            {
                'owner': edwyn_user,
                'name': 'Nala',
                'species': cat_species,
                'breed': 'Siamés',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 3, 12),
                'weight_kg': Decimal('4.20'),
                'certificate_type': 'Pedigrí certificado',
                'certificate_number': 'WCF-VE-2291',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Tranquila, Curiosa, Inteligente',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Nala es una gatita curiosa, estilizada y cariñosa con humanos y otros gatos tranquilos.',
            },
            {
                'owner': edwyn_user,
                'name': 'Coco',
                'species': dog_species,
                'breed': 'Poodle Toy',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 9, 1),
                'weight_kg': Decimal('3.80'),
                'certificate_type': 'En trámite',
                'certificate_number': 'TR-2023-441',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 10,
                'temperaments': 'Alegre, Sociable, Activa',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Poodle pequeña, muy simpática y le encanta compartir paseos cortos y juegos.',
            },
            # 3. Mascotas de Sofia
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
                'owner': sofia_user,
                'name': 'Bruno',
                'species': dog_species,
                'breed': 'Beagle',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 8, 14),
                'weight_kg': Decimal('13.50'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-44910',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Curioso, Enérgico, Amigable',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Beagle activo y alegre con excelente olfato y sociable con cualquier mascota.',
            },
            # 4. Mascotas de Maria
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
                'owner': maria_user,
                'name': 'Oliver',
                'species': dog_species,
                'breed': 'Schnauzer Mini',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2023, 1, 20),
                'weight_kg': Decimal('7.20'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-33812',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Leal, Inteligente, Guardián',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': 'Schnauzer cariñoso y obediente con excelente conducta.',
            },
            # 5. Mascotas de Bryan
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
                'owner': bryan_user,
                'name': 'Balto',
                'species': dog_species,
                'breed': 'Husky Siberiano',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2021, 11, 5),
                'weight_kg': Decimal('26.40'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-66290',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 30,
                'temperaments': 'Aventurero, Fuerte, Juguetón',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Husky de ojos celestes, adora caminatas por la montaña y climas templados.',
            },
            # 6. Mascotas de Oriana
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
            {
                'owner': oriana_user,
                'name': 'Leo',
                'species': cat_species,
                'breed': 'Bengala',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2023, 4, 18),
                'weight_kg': Decimal('5.10'),
                'certificate_type': 'Pedigrí certificado',
                'certificate_number': 'TICA-VE-8831',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Ágil, Activo, Curioso',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': 'Gato leopardo de bengala, atlético, amigable y muy juguetón.',
            },
            # 7. Mascotas de Stefany
            {
                'owner': stefany_user,
                'name': 'Rocky',
                'species': dog_species,
                'breed': 'Bulldog Francés',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 9, 2),
                'weight_kg': Decimal('12.00'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-77299',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Tranquilo, Afectuoso, Sociable',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Bulldog noble, adora las siestas y socializar tranquilamente en el parque.',
            },
            {
                'owner': stefany_user,
                'name': 'Mia',
                'species': cat_species,
                'breed': 'Persa',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2022, 12, 11),
                'weight_kg': Decimal('4.00'),
                'certificate_type': 'Pedigrí certificado',
                'certificate_number': 'WCF-VE-1104',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 10,
                'temperaments': 'Calmada, Mimosa, Silenciosa',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Gata persa de manto blanco esponjoso, adora caricias y ambientes calmados.',
            },
            # 8. Mascotas de Tutor
            {
                'owner': tutor_user,
                'name': 'Thor',
                'species': dog_species,
                'breed': 'Pastor Alemán',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2021, 7, 22),
                'weight_kg': Decimal('34.00'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-19920',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 25,
                'temperaments': 'Protector, Valiente, Obediente, Noble',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': 'Pastor Alemán de línea de trabajo, atlético, adiestrado y muy noble con la familia.',
            },
            {
                'owner': tutor_user,
                'name': 'Sasha',
                'species': dog_species,
                'breed': 'Golden Retriever',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2022, 10, 30),
                'weight_kg': Decimal('27.50'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-88319',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Sociable, Cariñosa, Alegre',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Golden Retriever dulce y sociable, le encanta nadar y buscar pelotas.',
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

        # ==============================================================================
        # Solicitudes de Match (MatchRequest) con estados variados e interactivos
        # ==============================================================================
        toby = created_pets.get('Toby')
        luna = created_pets.get('Luna')
        simba = created_pets.get('Simba')
        nala = created_pets.get('Nala')
        coco = created_pets.get('Coco')
        bella = created_pets.get('Bella')
        bruno = created_pets.get('Bruno')
        kira = created_pets.get('Kira')
        oliver = created_pets.get('Oliver')
        maya = created_pets.get('Maya')
        chloe = created_pets.get('Chloe')
        leo = created_pets.get('Leo')
        rocky = created_pets.get('Rocky')
        thor = created_pets.get('Thor')
        sasha = created_pets.get('Sasha')

        # 1. Solicitudes hacia Toby (admin)
        if toby and kira:
            req_kira, _ = MatchRequest.objects.update_or_create(
                from_pet=kira,
                to_pet=toby,
                defaults={
                    'status': MatchRequest.RequestStatus.ACCEPTED,
                    'notes': '¡Hola! Nos encantó Toby. Kira es súper dócil y juguetona. Buscamos encuentro de socialización.',
                },
            )
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
                    'notes': 'Chloe busca amigos de su misma raza para tardes de juego en el parque.',
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

        # 2. Solicitudes hacia Simba (edwyn - usuario principal de pruebas)
        if simba and luna:
            req_luna_simba, _ = MatchRequest.objects.update_or_create(
                from_pet=luna,
                to_pet=simba,
                defaults={
                    'status': MatchRequest.RequestStatus.ACCEPTED,
                    'notes': '¡Match de Golden Retrievers! Luna adora correr en campos abiertos y Simba es un gran compañero.',
                },
            )
            PetMeetup.objects.update_or_create(
                pet1=simba,
                pet2=luna,
                date=date(2026, 10, 25),
                defaults={
                    'match_request': req_luna_simba,
                    'time': time(10, 0),
                    'location_name': 'Parque del Este (Área Verde Canina)',
                    'status': PetMeetup.MeetupStatus.CONFIRMED,
                    'notes': 'Cita de socialización confirmada entre tutores verificados.',
                },
            )

        if simba and sasha:
            req_sasha_simba, _ = MatchRequest.objects.update_or_create(
                from_pet=sasha,
                to_pet=simba,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Sasha también es Golden Retriever. Nos gustaría coordinar un encuentro en Parque Vizcaya.',
                },
            )
            PetMeetup.objects.update_or_create(
                pet1=simba,
                pet2=sasha,
                date=date(2026, 11, 2),
                defaults={
                    'match_request': req_sasha_simba,
                    'time': time(16, 30),
                    'location_name': 'Parque Vizcaya (Zona de Mascotas)',
                    'status': PetMeetup.MeetupStatus.PROPOSED,
                    'notes': 'Cita propuesta pendiente de confirmación mutua.',
                },
            )

        if simba and bella:
            MatchRequest.objects.update_or_create(
                from_pet=bella,
                to_pet=simba,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'A Bella le gustaría compartir paseos activos con Simba.',
                },
            )

        if simba and kira:
            MatchRequest.objects.update_or_create(
                from_pet=simba,
                to_pet=kira,
                defaults={
                    'status': MatchRequest.RequestStatus.REJECTED,
                    'notes': 'Solicitud descartada por diferencia considerable de peso y tamaño.',
                },
            )

        # 3. Interacciones adicionales entre otros usuarios (para poblar el sistema)
        if rocky and chloe:
            req_rocky_chloe, _ = MatchRequest.objects.update_or_create(
                from_pet=rocky,
                to_pet=chloe,
                defaults={
                    'status': MatchRequest.RequestStatus.ACCEPTED,
                    'notes': 'Ambos Bulldogs Franceses certificados FCI, excelente afinidad y temperamento.',
                },
            )
            PetMeetup.objects.update_or_create(
                pet1=rocky,
                pet2=chloe,
                date=date(2026, 10, 22),
                defaults={
                    'match_request': req_rocky_chloe,
                    'time': time(15, 0),
                    'location_name': 'Parque Los Caobos (Circuito Canino)',
                    'status': PetMeetup.MeetupStatus.CONFIRMED,
                    'notes': 'Cita de juego entre cachorros de la misma raza.',
                },
            )

        if bruno and maya:
            MatchRequest.objects.update_or_create(
                from_pet=bruno,
                to_pet=maya,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Bruno es muy enérgico y le encantaría correr junto a Maya.',
                },
            )

        if thor and luna:
            req_thor_luna, _ = MatchRequest.objects.update_or_create(
                from_pet=thor,
                to_pet=luna,
                defaults={
                    'status': MatchRequest.RequestStatus.REJECTED,
                    'notes': 'Solicitud cancelada por distancia geográfica.',
                },
            )
            PetMeetup.objects.update_or_create(
                pet1=thor,
                pet2=luna,
                date=date(2026, 10, 5),
                defaults={
                    'match_request': req_thor_luna,
                    'time': time(16, 0),
                    'location_name': 'Parque El Paraíso',
                    'status': PetMeetup.MeetupStatus.CANCELLED,
                    'notes': 'Encuentro cancelado por lluvia intensa.',
                },
            )

        if oliver and coco:
            MatchRequest.objects.update_or_create(
                from_pet=oliver,
                to_pet=coco,
                defaults={
                    'status': MatchRequest.RequestStatus.PENDING,
                    'notes': 'Oliver busca perritas de tamaño toy para socialización.',
                },
            )

        if leo and nala:
            MatchRequest.objects.update_or_create(
                from_pet=leo,
                to_pet=nala,
                defaults={
                    'status': MatchRequest.RequestStatus.ACCEPTED,
                    'notes': 'Match felino para socialización en hogar cerrado supervisado.',
                },
            )

        # Cita completada histórica para simular reputación y citas pasadas
        if bruno and bella:
            PetMeetup.objects.update_or_create(
                pet1=bruno,
                pet2=bella,
                date=date(2026, 9, 15),
                defaults={
                    'time': time(10, 0),
                    'location_name': 'Parque La Rosaleda (Los Teques)',
                    'status': PetMeetup.MeetupStatus.COMPLETED,
                    'notes': 'Encuentro completado con éxito, excelente conducta de ambas mascotas.',
                },
            )

        # ==============================================================================
        # Reportes de prueba (UserReport) para auditoría y moderación
        # ==============================================================================
        if tutor_user and admin_user:
            UserReport.objects.update_or_create(
                reported_by=admin_user,
                reported_user=tutor_user,
                reported_pet=thor,
                defaults={
                    'reason': 'Paseo de mascota sin correa en área común fuera del circuito canino cercado.',
                    'status': UserReport.ReportStatus.PENDING,
                    'admin_notes': 'Pendiente de contactar al tutor para recordatorio de normas de convivencia.',
                },
            )

        self.stdout.write(
            self.style.SUCCESS('¡Semilla de mascotas, match y citas completada exitosamente!')
        )
