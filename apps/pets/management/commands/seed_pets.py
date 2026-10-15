"""
Comando de gestión para enriquecer y poblar la base de datos de desarrollo de Petly
con datos completos: especies, usuarios, mascotas diversas, solicitudes de match
en todos los estados (interesados, solicitudes, matches) y agendas de citas.
"""

from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile, UserReport
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies

User = get_user_model()

DEV_PASSWORD = '123456789'


class Command(BaseCommand):
    help = 'Carga mascotas de prueba, solicitudes de match y citas de socialización con datos diversos y equilibrados'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE('Iniciando carga de datos semilla para el módulo de match...')
        )

        # ==============================================================================
        # 1. Asegurar contraseña unificada (123456789) para todos los usuarios de desarrollo
        # ==============================================================================
        dev_usernames = [
            'admin',
            'edwyn',
            'stefany',
            'bryan',
            'oriana',
            'maria',
            'sofia',
            'tutor',
        ]
        for uname in dev_usernames:
            user = User.objects.filter(username=uname).first()
            if user:
                user.set_password(DEV_PASSWORD)
                user.is_active = True
                user.save()
                self.stdout.write(
                    f'  ✓ Credenciales verificadas para {uname} (clave: {DEV_PASSWORD})'
                )

        # ==============================================================================
        # 2. Catálogo oficial de especies
        # ==============================================================================
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

        # ==============================================================================
        # 3. Perfiles de usuario con geolocalización y preferencias en Caracas / Miranda
        # ==============================================================================
        user_profiles_data = {
            'admin': {
                'state': 'Distrito Capital',
                'municipality': 'Libertador',
                'neighborhood': 'La Candelaria',
                'favorite_color': 'Coral',
                'favorite_book': 'El principito',
                'favorite_music': 'Rock clásico',
                'favorite_videogame': 'Super Mario',
                'gender': 'M',
                'latitude': 10.5060,
                'longitude': -66.9146,
            },
            'edwyn': {
                'state': 'Miranda',
                'municipality': 'Chacao',
                'neighborhood': 'Los Palos Grandes',
                'favorite_color': 'Azul',
                'favorite_book': 'Clean Code',
                'favorite_music': 'Synthwave',
                'favorite_videogame': 'The Witcher',
                'gender': 'M',
                'latitude': 10.4990,
                'longitude': -66.8480,
            },
            'stefany': {
                'state': 'Miranda',
                'municipality': 'Baruta',
                'neighborhood': 'Las Mercedes',
                'favorite_color': 'Rosa',
                'favorite_book': 'Orgullo y prejuicio',
                'favorite_music': 'Indie Pop',
                'favorite_videogame': 'Stardew Valley',
                'gender': 'F',
                'latitude': 10.4780,
                'longitude': -66.8620,
            },
            'tutor': {
                'state': 'Miranda',
                'municipality': 'Los Salias',
                'neighborhood': 'San Antonio de Los Altos',
                'favorite_color': 'Verde',
                'favorite_book': 'Sapiens',
                'favorite_music': 'Acústica',
                'favorite_videogame': 'Minecraft',
                'gender': 'M',
                'latitude': 10.3750,
                'longitude': -66.9530,
            },
            'sofia': {
                'state': 'Miranda',
                'municipality': 'Guaicaipuro',
                'neighborhood': 'Los Teques Centro',
                'favorite_color': 'Coral',
                'favorite_book': 'Harry Potter',
                'favorite_music': 'Indie Rock',
                'favorite_videogame': 'Animal Crossing',
                'gender': 'F',
                'latitude': 10.3440,
                'longitude': -67.0420,
            },
            'maria': {
                'state': 'Distrito Capital',
                'municipality': 'Libertador',
                'neighborhood': 'El Recreo',
                'favorite_color': 'Lila',
                'favorite_book': 'Cien años de soledad',
                'favorite_music': 'Pop',
                'favorite_videogame': 'The Sims',
                'gender': 'F',
                'latitude': 10.4930,
                'longitude': -66.8790,
            },
            'bryan': {
                'state': 'Miranda',
                'municipality': 'El Hatillo',
                'neighborhood': 'El Hatillo Pueblo',
                'favorite_color': 'Menta',
                'favorite_book': 'Dune',
                'favorite_music': 'Electrónica',
                'favorite_videogame': 'Zelda: Breath of the Wild',
                'gender': 'M',
                'latitude': 10.4280,
                'longitude': -66.8250,
            },
            'oriana': {
                'state': 'Miranda',
                'municipality': 'Sucre',
                'neighborhood': 'Los Dos Caminos',
                'favorite_color': 'Melocotón',
                'favorite_book': 'El Hobbit',
                'favorite_music': 'R&B',
                'favorite_videogame': 'Pokemon',
                'gender': 'F',
                'latitude': 10.4940,
                'longitude': -66.8320,
            },
        }

        for username, p_data in user_profiles_data.items():
            user = User.objects.filter(username=username).first()
            if user:
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults=p_data,
                )

        # Limpiar referencias huérfanas a archivos de avatar inexistentes en disco
        for prof in UserProfile.objects.exclude(avatar='').exclude(avatar=None):
            if prof.avatar and hasattr(prof.avatar, 'storage'):
                try:
                    if not prof.avatar.storage.exists(prof.avatar.name):
                        prof.avatar = None
                        prof.save(update_fields=['avatar'])
                except Exception:
                    pass

        # Limpiar referencias huérfanas a fotos de mascotas inexistentes en disco
        for pt in Pet.objects.exclude(photo='').exclude(photo=None):
            if pt.photo and hasattr(pt.photo, 'storage'):
                try:
                    if not pt.photo.storage.exists(pt.photo.name):
                        pt.photo = None
                        pt.save(update_fields=['photo'])
                except Exception:
                    pass

        admin_user = User.objects.filter(username='admin').first() or User.objects.first()
        edwyn_user = User.objects.filter(username='edwyn').first() or admin_user
        stefany_user = User.objects.filter(username='stefany').first() or admin_user
        tutor_user = User.objects.filter(username='tutor').first() or admin_user
        sofia_user = User.objects.filter(username='sofia').first() or admin_user
        maria_user = User.objects.filter(username='maria').first() or admin_user
        bryan_user = User.objects.filter(username='bryan').first() or admin_user
        oriana_user = User.objects.filter(username='oriana').first() or admin_user

        # ==============================================================================
        # 4. Mascotas de la plataforma para TODOS los usuarios
        # ==============================================================================
        pets_spec = [
            # --- 1. Mascotas de Admin ---
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
                'description': 'Adora correr en el parque, jugar con pelotas y dormir siestas al sol. Muy amigable con otros perros.',
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
            {
                'owner': admin_user,
                'name': 'Zeus',
                'species': dog_species,
                'breed': 'Pastor Alemán',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 1, 10),
                'weight_kg': Decimal('35.00'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-99101',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 25,
                'temperaments': 'Protector, Leal, Inteligente',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Pastor Alemán noble y atento, excelente guardián y compañero de trote.',
            },
            # --- 2. Mascotas de Edwyn (Usuario desarrollador principal) ---
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
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 10,
                'temperaments': 'Alegre, Sociable, Activa',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Poodle pequeña, muy simpática y le encanta compartir paseos cortos y juegos.',
            },
            {
                'owner': edwyn_user,
                'name': 'Max',
                'species': dog_species,
                'breed': 'Husky Siberiano',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 11, 20),
                'weight_kg': Decimal('25.50'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-33210',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 30,
                'temperaments': 'Aventurero, Energético, Curioso',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Husky juguetón y sociable que adora correr al aire libre y hacer nuevos amigos caninos.',
            },
            # --- 3. Mascotas de Stefany ---
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
            {
                'owner': stefany_user,
                'name': 'Canela',
                'species': dog_species,
                'breed': 'Golden Retriever',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 2, 14),
                'weight_kg': Decimal('27.00'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-55410',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Cariñosa, Enérgica, Nadadora',
                'profile_color': Pet.ProfileColor.CORAL,
                'description': 'Golden Retriever jovial y dulce, le fascina jugar con la pelota y compartir con otros perros.',
            },
            # --- 4. Mascotas de Sofia ---
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
                'description': 'Bella es una perrita alegre, noble y muy inteligente. Adora correr al aire libre y convivir en armonía.',
            },
            {
                'owner': sofia_user,
                'name': 'Bruno',
                'species': dog_species,
                'breed': 'Beagle',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 8, 14),
                'weight_kg': Decimal('13.50'),
                'certificate_type': 'Sin pedigrí',
                'certificate_number': '',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Curioso, Enérgico, Amigable',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Beagle activo y alegre con excelente olfato y sociable con cualquier mascota.',
            },
            {
                'owner': sofia_user,
                'name': 'Pelusa',
                'species': cat_species,
                'breed': 'Angora Turco',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 10, 1),
                'weight_kg': Decimal('3.80'),
                'certificate_type': 'Sin pedigrí',
                'certificate_number': '',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 25,
                'temperaments': 'Curiosa, Esponjosa, Mansa',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Gatita de pelaje sedoso y esponjoso, muy curiosa y acostumbrada a convivir en armonía.',
            },
            # --- 5. Mascotas de Maria ---
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
                'description': 'Kira es súper dócil, tierna y juguetona en calma. Buscamos una cruza ética certificada.',
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
            {
                'owner': maria_user,
                'name': 'Milo',
                'species': dog_species,
                'breed': 'Golden Retriever',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 7, 4),
                'weight_kg': Decimal('29.80'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-77612',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Amigable, Protector, Juguetón',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Golden Retriever dócil y equilibrado, perfecto compañero de paseos largos.',
            },
            # --- 6. Mascotas de Bryan ---
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
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Curiosa, Juguetona, Protectora',
                'profile_color': Pet.ProfileColor.MINT,
                'description': 'Maya es activa, adora los paseos largos por el parque y jugar con pelotas.',
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
            {
                'owner': bryan_user,
                'name': 'Lucas',
                'species': cat_species,
                'breed': 'British Shorthair',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2023, 8, 15),
                'weight_kg': Decimal('4.60'),
                'certificate_type': 'Sin pedigrí',
                'certificate_number': '',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 25,
                'temperaments': 'Dócil, Silencioso, Tierno',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Gato británico de pelaje gris denso, tranquilo, cariñoso y de andar elegante.',
            },
            # --- 7. Mascotas de Oriana ---
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
                'temperaments': 'Juguetona, Cariñosa, Vivaz',
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
            {
                'owner': oriana_user,
                'name': 'Princesa',
                'species': dog_species,
                'breed': 'Poodle Toy',
                'gender': Pet.Gender.HEMBRA,
                'birth_date': date(2023, 5, 20),
                'weight_kg': Decimal('3.50'),
                'certificate_type': 'Certificado FCI',
                'certificate_number': 'FCI-VE-44102',
                'purpose': Pet.Purpose.BOTH,
                'is_active_for_match': True,
                'max_search_distance_km': 15,
                'temperaments': 'Coqueta, Dulce, Sociable',
                'profile_color': Pet.ProfileColor.LILAC,
                'description': 'Poodle Toy elegante y dócil, excelente compañía.',
            },
            # --- 8. Mascotas de Tutor ---
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
            {
                'owner': tutor_user,
                'name': 'Garfield',
                'species': cat_species,
                'breed': 'Maine Coon',
                'gender': Pet.Gender.MACHO,
                'birth_date': date(2022, 4, 5),
                'weight_kg': Decimal('7.50'),
                'certificate_type': 'Pedigrí certificado',
                'certificate_number': 'WCF-VE-3301',
                'purpose': Pet.Purpose.PLAY,
                'is_active_for_match': True,
                'max_search_distance_km': 20,
                'temperaments': 'Manso, Gigante noble, Tierno',
                'profile_color': Pet.ProfileColor.PEACH,
                'description': 'Maine Coon majestuoso, peludo, ronroneador y muy sociable con otros animales.',
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
            self.stdout.write(f'  • Mascota {pet.name} de {pet.owner.username} ({status})')

        # Asignar variables directas para construir relaciones y citas
        toby = created_pets.get('Toby')
        luna = created_pets.get('Luna')
        zeus = created_pets.get('Zeus')

        simba = created_pets.get('Simba')
        nala = created_pets.get('Nala')
        coco = created_pets.get('Coco')
        max_pet = created_pets.get('Max')

        rocky = created_pets.get('Rocky')
        canela = created_pets.get('Canela')

        bella = created_pets.get('Bella')
        bruno = created_pets.get('Bruno')
        pelusa = created_pets.get('Pelusa')

        kira = created_pets.get('Kira')
        oliver = created_pets.get('Oliver')

        maya = created_pets.get('Maya')
        balto = created_pets.get('Balto')
        lucas = created_pets.get('Lucas')

        chloe = created_pets.get('Chloe')
        leo = created_pets.get('Leo')

        thor = created_pets.get('Thor')
        sasha = created_pets.get('Sasha')
        garfield = created_pets.get('Garfield')

        # ==============================================================================
        # 5. Solicitudes de Match (MatchRequest) ricas para todos los usuarios
        # ==============================================================================
        # Helper para registrar solicitudes y citas
        def create_match_req(from_p, to_p, status, notes):
            if from_p and to_p and from_p != to_p and from_p.owner_id != to_p.owner_id:
                req, _ = MatchRequest.objects.update_or_create(
                    from_pet=from_p,
                    to_pet=to_p,
                    defaults={'status': status, 'notes': notes},
                )
                return req
            return None

        # --- A. Relaciones para EDWYN ---
        # 1. Simba (Golden Retriever Macho)
        # Recibidas PENDING (Interesados para Simba):
        req_sasha_simba = create_match_req(
            sasha,
            simba,
            MatchRequest.RequestStatus.PENDING,
            '¡Hola Edwyn! Sasha también es Golden Retriever con pedigrí FCI. Nos gustaría coordinar un encuentro en Parque Vizcaya.',
        )
        create_match_req(
            bella,
            simba,
            MatchRequest.RequestStatus.PENDING,
            'A Bella le encantaría compartir paseos activos y correr con Simba en Los Salias.',
        )
        create_match_req(
            canela,
            simba,
            MatchRequest.RequestStatus.PENDING,
            'Canela busca compañeros de su misma raza para nadar y jugar en Parque del Este.',
        )

        # Enviadas PENDING (Solicitudes enviadas desde Simba):
        create_match_req(
            simba,
            chloe,
            MatchRequest.RequestStatus.PENDING,
            '¡Hola Oriana! Me pareció muy linda Chloe, ¿les gustaría coincidir en el parque canino de Los Dos Caminos?',
        )
        create_match_req(
            simba,
            maya,
            MatchRequest.RequestStatus.PENDING,
            'Simba busca amigos activos para jugar al aire libre y correr juntos.',
        )

        # Aceptadas (Matches mutuos de Simba):
        req_luna_simba = create_match_req(
            luna,
            simba,
            MatchRequest.RequestStatus.ACCEPTED,
            '¡Match mutuo de Golden Retrievers! Luna adora correr en campos abiertos y Simba es un gran compañero.',
        )

        # Rechazada:
        create_match_req(
            simba,
            kira,
            MatchRequest.RequestStatus.REJECTED,
            'Solicitud descartada cordialmente por amplia diferencia de tamaño corporal.',
        )

        # 2. Coco (Poodle Toy Hembra)
        req_oliver_coco = create_match_req(
            oliver,
            coco,
            MatchRequest.RequestStatus.ACCEPTED,
            '¡Oliver y Coco son ideales para socializar por peso y tamaño!',
        )
        create_match_req(
            bruno,
            coco,
            MatchRequest.RequestStatus.PENDING,
            'Bruno busca amigas pequeñas para paseos tranquilos.',
        )
        create_match_req(
            coco,
            rocky,
            MatchRequest.RequestStatus.PENDING,
            'Coco quiere conocer a Rocky para tardes de juego.',
        )

        # 3. Nala (Gata Siamés)
        req_leo_nala = create_match_req(
            leo,
            nala,
            MatchRequest.RequestStatus.ACCEPTED,
            'Match felino para socialización en hogar cerrado y supervisado.',
        )
        create_match_req(
            garfield,
            nala,
            MatchRequest.RequestStatus.PENDING,
            'Garfield es un Maine Coon sociable y tranquilo. ¿Quieren organizar una visita?',
        )

        # 4. Max (Husky Siberiano Macho)
        create_match_req(
            max_pet,
            bella,
            MatchRequest.RequestStatus.PENDING,
            'Max busca compañeros ágiles para correr largas distancias por la montaña.',
        )

        # --- B. Relaciones entre otros usuarios ---
        # Toby (Admin)
        req_toby_kira = create_match_req(
            kira,
            toby,
            MatchRequest.RequestStatus.ACCEPTED,
            'Kira es súper dócil y juguetona. Buscamos encuentro de socialización.',
        )
        req_toby_chloe = create_match_req(
            chloe,
            toby,
            MatchRequest.RequestStatus.ACCEPTED,
            'Ambos Bulldogs Franceses certificados, excelente afinidad.',
        )
        create_match_req(
            maya,
            toby,
            MatchRequest.RequestStatus.PENDING,
            'Maya busca compañeros de juego en La Candelaria.',
        )

        # Rocky (Stefany)
        req_rocky_chloe = create_match_req(
            rocky,
            chloe,
            MatchRequest.RequestStatus.ACCEPTED,
            'Ambos Bulldogs Franceses certificados FCI, excelente afinidad y temperamento.',
        )

        # Thor (Tutor)
        req_thor_zeus = create_match_req(
            thor,
            zeus,
            MatchRequest.RequestStatus.ACCEPTED,
            'Encuentro de socialización entre Pastores Alemanes certificados.',
        )
        req_thor_luna = create_match_req(
            thor,
            luna,
            MatchRequest.RequestStatus.REJECTED,
            'Solicitud cancelada por distancia geográfica.',
        )

        # Balto (Bryan)
        req_balto_bella = create_match_req(
            balto,
            bella,
            MatchRequest.RequestStatus.ACCEPTED,
            'Compañeros ideales para caminatas y senderismo en El Hatillo.',
        )

        # Gatos (Lucas y Pelusa)
        req_lucas_pelusa = create_match_req(
            lucas,
            pelusa,
            MatchRequest.RequestStatus.ACCEPTED,
            '¡Match especial de gatos! Socialización supervisada en área de juego protegida.',
        )

        # Bruno (Sofia) y Maya (Bryan)
        req_bruno_maya = create_match_req(
            bruno,
            maya,
            MatchRequest.RequestStatus.ACCEPTED,
            'Bruno y Maya tienen gran afinidad para correr juntos en parques abiertos.',
        )

        # ==============================================================================
        # 6. Agendas y Citas Presenciales (PetMeetup) con variedad de estados y fechas
        # ==============================================================================
        # Helper para meetups
        def create_meetup(p1, p2, m_req, d, t, loc, status, notes):
            if p1 and p2 and p1 != p2 and p1.owner_id != p2.owner_id:
                meetup, _ = PetMeetup.objects.update_or_create(
                    pet1=p1,
                    pet2=p2,
                    date=d,
                    defaults={
                        'match_request': m_req,
                        'time': t,
                        'location_name': loc,
                        'status': status,
                        'notes': notes,
                    },
                )
                return meetup
            return None

        # 1. Cita confirmada para Simba y Luna (Próxima, Octubre 2026)
        create_meetup(
            simba,
            luna,
            req_luna_simba,
            date(2026, 10, 25),
            time(10, 0),
            'Parque Generalísimo Francisco de Miranda (Parque del Este) - Área Canina',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Cita de socialización canina confirmada entre tutores verificados. Traer hidratación y pelotas.',
        )

        # 2. Cita propuesta para Simba y Sasha (Noviembre 2026)
        create_meetup(
            simba,
            sasha,
            req_sasha_simba,
            date(2026, 11, 2),
            time(16, 30),
            'Parque Vizcaya (Zona Canina Cercada)',
            PetMeetup.MeetupStatus.PROPOSED,
            'Cita propuesta pendiente de confirmación mutua de horarios.',
        )

        # 3. Cita confirmada para Coco y Oliver (Octubre 2026)
        create_meetup(
            coco,
            oliver,
            req_oliver_coco,
            date(2026, 10, 28),
            time(15, 0),
            'Plaza Los Palos Grandes - Área de Mascotas',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Cita de café pet-friendly para que Coco y Oliver compartan en calma.',
        )

        # 4. Cita completada histórica para Nala y Leo (Septiembre 2026)
        create_meetup(
            nala,
            leo,
            req_leo_nala,
            date(2026, 9, 28),
            time(16, 0),
            'Terraza Pet-Friendly Los Dos Caminos (Área Cerrada)',
            PetMeetup.MeetupStatus.COMPLETED,
            'Encuentro completado con éxito, excelente química entre felinos.',
        )

        # 5. Cita confirmada para Toby y Kira (Admin)
        create_meetup(
            toby,
            kira,
            req_toby_kira,
            date(2026, 10, 18),
            time(11, 0),
            'Parque España (Zona Canina Verificada)',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Encuentro inicial de socialización canina supervisado en espacio cercado.',
        )

        # 6. Cita confirmada para Toby y Chloe (Admin & Oriana)
        create_meetup(
            toby,
            chloe,
            req_toby_chloe,
            date(2026, 10, 22),
            time(11, 0),
            'Parque Los Caobos (Circuito Canino)',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Tarde de juegos entre cachorros Bulldogs Franceses.',
        )

        # 7. Cita confirmada para Rocky y Chloe (Stefany & Oriana)
        create_meetup(
            rocky,
            chloe,
            req_rocky_chloe,
            date(2026, 10, 20),
            time(16, 30),
            'Parque Las Mercedes - Canil Municipal',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Cita de socialización confirmada entre tutoras de Baruta y Sucre.',
        )

        # 8. Cita propuesta para Thor y Zeus (Tutor & Admin)
        create_meetup(
            thor,
            zeus,
            req_thor_zeus,
            date(2026, 11, 8),
            time(9, 30),
            'Parque La Rosaleda (San Antonio de Los Altos)',
            PetMeetup.MeetupStatus.PROPOSED,
            'Entrenamiento conjunto y socialización de razas grandes.',
        )

        # 9. Cita confirmada para Balto y Bella (Bryan & Sofia)
        create_meetup(
            balto,
            bella,
            req_balto_bella,
            date(2026, 10, 30),
            time(8, 30),
            'Mirador El Hatillo - Senderismo Canino Ecológico',
            PetMeetup.MeetupStatus.CONFIRMED,
            'Caminata de montaña con arnés de senderismo.',
        )

        # 10. Cita completada para Bruno y Maya (Sofia & Bryan)
        create_meetup(
            bruno,
            maya,
            req_bruno_maya,
            date(2026, 9, 15),
            time(10, 0),
            'Parque Gustavo Knoop (Los Teques)',
            PetMeetup.MeetupStatus.COMPLETED,
            'Encuentro completado con éxito, excelente conducta de ambas mascotas.',
        )

        # 11. Cita cancelada para Thor y Luna
        create_meetup(
            thor,
            luna,
            req_thor_luna,
            date(2026, 10, 5),
            time(17, 0),
            'Parque El Paraíso',
            PetMeetup.MeetupStatus.CANCELLED,
            'Encuentro cancelado por fuertes precipitaciones.',
        )

        # Cita propuesta para Lucas y Pelusa (Gatos)
        create_meetup(
            lucas,
            pelusa,
            req_lucas_pelusa,
            date(2026, 11, 5),
            time(15, 30),
            'Café Felino & Lounge - Sala Privada',
            PetMeetup.MeetupStatus.PROPOSED,
            'Encuentro especial en lounge protegido para gatos.',
        )

        # ==============================================================================
        # 7. Reportes de prueba (UserReport) para auditoría y moderación
        # ==============================================================================
        if tutor_user and admin_user and thor:
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
            self.style.SUCCESS(
                '¡Semilla de mascotas, match y citas enriquecida y completada exitosamente!'
            )
        )
