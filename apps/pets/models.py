import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class PetSpecies(TimeStampedModel):
    """
    Catálogo de especies de mascotas disponibles en la plataforma.
    Permite a los administradores registrar y gestionar especies (ej. Perro, Gato, Conejo)
    sin modificar el código de la aplicación.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Nombre'),
        help_text=_('Nombre común de la especie (ej. Perro, Gato, Conejo).'),
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name=_('Identificador'),
        help_text=_('Identificador en minúsculas para URLs y filtros (ej. perro, gato).'),
    )
    icon_name = models.CharField(
        max_length=50,
        default='paw',
        blank=True,
        verbose_name=_('Ícono'),
        help_text=_('Nombre del ícono SVG asociado (ej. dog, paw, sparkles).'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Indica si la especie está disponible para registro y búsqueda.'),
    )

    class Meta:
        verbose_name = _('Especie')
        verbose_name_plural = _('Catálogo de especies')
        ordering = ['name']

    def __str__(self):
        return self.name


def pet_photo_upload_path(instance, filename):
    """
    Genera la ruta de almacenamiento para fotos de mascotas siguiendo
    la convención autodescriptiva definida en README.md:
    pets/user_{owner_id}_pet_{pet_id}_{tipo}_{id_unico}.{ext}
    Ejemplo: pets/user_42_pet_7_avatar_9f8e7d6c.jpg
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    owner_id = instance.owner_id or getattr(instance.owner, 'id', 'unknown')
    pet_id = instance.pk or 'new'
    tipo = 'avatar'
    id_unico = uuid.uuid4().hex[:8]
    return f'pets/user_{owner_id}_pet_{pet_id}_{tipo}_{id_unico}.{ext}'


class Pet(TimeStampedModel):
    """
    Representa una mascota registrada por un tutor en Petly.
    Permite participar en el módulo de emparejamiento (match feed),
    citas de socialización y acuerdos de cruza ética.
    """

    class Gender(models.TextChoices):
        MACHO = 'M', _('Macho')
        HEMBRA = 'H', _('Hembra')

    # Alias de compatibilidad hacia atrás
    Gender.MALE = Gender.MACHO
    Gender.FEMALE = Gender.HEMBRA

    class Purpose(models.TextChoices):
        MATING = 'mating', _('Cruza responsable')
        PLAY = 'play', _('Socialización')
        BOTH = 'both', _('Cruza y socialización')

    class ProfileColor(models.TextChoices):
        CORAL = 'coral', _('Coral')
        LILAC = 'lilac', _('Lila')
        MINT = 'mint', _('Menta')
        PEACH = 'peach', _('Melocotón')

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pets',
        verbose_name=_('Tutor / Dueño'),
        help_text=_('Usuario tutor propietario de la mascota.'),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre'),
        help_text=_('Nombre oficial de la mascota.'),
    )
    species = models.ForeignKey(
        PetSpecies,
        on_delete=models.PROTECT,
        related_name='pets',
        verbose_name=_('Especie'),
        help_text=_('Especie de la mascota seleccionada del catálogo.'),
    )
    breed = models.CharField(
        max_length=100,
        verbose_name=_('Raza'),
        help_text=_('Raza de la mascota (ej. Bulldog Francés, Golden Retriever).'),
    )
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        default=Gender.MACHO,
        verbose_name=_('Sexo'),
        help_text=_('Sexo biológico de la mascota (M: Macho, H: Hembra).'),
    )
    birth_date = models.DateField(
        verbose_name=_('Fecha de nacimiento'),
        help_text=_('Fecha de nacimiento para cálculo exacto de edad.'),
    )
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Peso (kg)'),
        help_text=_('Peso corporal actual en kilogramos.'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción'),
        help_text=_('Biografía, temperamento y preferencias de la mascota.'),
    )
    photo = models.ImageField(
        upload_to=pet_photo_upload_path,
        blank=True,
        null=True,
        verbose_name=_('Fotografía'),
        help_text=_('Fotografía principal de la mascota para el feed y perfil.'),
    )
    certificate_type = models.CharField(
        max_length=100,
        blank=True,
        default='Certificado FCI',
        verbose_name=_('Tipo de certificado'),
        help_text=_('Certificación sanitaria o de pedigrí (ej. Certificado FCI).'),
    )
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Número de certificado'),
        help_text=_('Número de registro oficial o folio del certificado.'),
    )
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.BOTH,
        verbose_name=_('Propósito'),
        help_text=_('Objetivo de búsqueda (cruza, socialización o ambos).'),
    )
    is_active_for_match = models.BooleanField(
        default=True,
        verbose_name=_('Activo para match'),
        help_text=_('Determina si la mascota es visible en el feed de búsqueda de parejas.'),
    )
    max_search_distance_km = models.PositiveIntegerField(
        default=50,
        verbose_name=_('Distancia máxima de búsqueda (km)'),
        help_text=_('Radio máximo en kilómetros para evaluar candidatos.'),
    )
    temperaments = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Temperamentos'),
        help_text=_('Rasgos separados por coma (ej. Juguetón, Sociable, Cariñoso).'),
    )
    profile_color = models.CharField(
        max_length=20,
        choices=ProfileColor.choices,
        default=ProfileColor.CORAL,
        verbose_name=_('Color de perfil'),
        help_text=_('Color temático del perfil de la mascota.'),
    )

    class Meta:
        verbose_name = _('Mascota')
        verbose_name_plural = _('Mascotas')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.species_label} - {self.breed})'

    @property
    def species_label(self):
        if not self.species:
            return _('Mascota')
        if hasattr(self.species, 'name'):
            return self.species.name
        return str(self.species).strip().capitalize()

    @property
    def age_years(self):
        if not self.birth_date:
            return 0
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    @property
    def age_text(self):
        years = self.age_years
        if years == 1:
            return _('1 año')
        elif years > 1:
            return _(f'{years} años')
        if not self.birth_date:
            return _('Edad no especificada')
        today = date.today()
        months = (today.year - self.birth_date.year) * 12 + today.month - self.birth_date.month
        if months <= 1:
            return _('1 mes')
        return _(f'{months} meses')

    @property
    def age(self):
        return self.age_text

    @property
    def is_macho(self):
        return self.gender in (self.Gender.MACHO, 'M', 'macho')

    @property
    def is_hembra(self):
        return self.gender in (self.Gender.HEMBRA, 'H', 'hembra', 'F')

    @property
    def gender_icon(self):
        return 'male' if self.is_macho else 'female'

    @property
    def gender_label(self):
        if self.is_macho:
            return _('Macho')
        if self.is_hembra:
            return _('Hembra')
        return self.get_gender_display()

    @property
    def photo_url(self):
        if self.photo and hasattr(self.photo, 'name') and self.photo.name:
            try:
                return self.photo.url
            except ValueError:
                pass
        return f'{settings.STATIC_URL}images/pets/default_avatar.svg'

    @property
    def has_photo(self):
        return bool(self.photo and hasattr(self.photo, 'name') and self.photo.name)

    @property
    def photo_clean_url(self):
        return self.photo_url

    @property
    def temperament_list(self):
        if not self.temperaments:
            return []
        return [t.strip() for t in self.temperaments.split(',') if t.strip()]

    @property
    def profile_color_hex(self):
        color_map = {
            self.ProfileColor.CORAL: '#FA7D82',
            self.ProfileColor.LILAC: '#E9D5FF',
            self.ProfileColor.MINT: '#8FFFB4',
            self.ProfileColor.PEACH: '#FFDAD9',
        }
        return color_map.get(self.profile_color, '#FA7D82')

    @property
    def has_pedigree(self):
        return bool(self.certificate_number or 'fci' in (self.certificate_type or '').lower())

    @property
    def location(self):
        if hasattr(self.owner, 'profile') and self.owner.profile.city:
            return self.owner.profile.city
        return 'Caracas'


class MatchRequest(TimeStampedModel):
    """
    Solicitud de conexión o interés enviada desde una mascota hacia otra
    durante la exploración en el feed de emparejamiento.
    """

    class RequestStatus(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        ACCEPTED = 'accepted', _('Aceptada')
        REJECTED = 'rejected', _('Rechazada')

    from_pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='sent_match_requests',
        verbose_name=_('Mascota solicitante'),
    )
    to_pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='received_match_requests',
        verbose_name=_('Mascota solicitada'),
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name=_('Estado de la solicitud'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Nota de solicitud'),
        help_text=_('Nota enviada por el tutor solicitante.'),
    )

    class Meta:
        verbose_name = _('Solicitud de match')
        verbose_name_plural = _('Solicitudes de match')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['from_pet', 'to_pet'],
                name='unique_match_request_between_pets',
            ),
            models.CheckConstraint(
                condition=~models.Q(from_pet=models.F('to_pet')),
                name='prevent_self_match_request',
            ),
        ]

    def __str__(self):
        return f'{self.from_pet.name} ➔ {self.to_pet.name} ({self.get_status_display()})'


class PetMeetup(TimeStampedModel):
    """
    Encuentro o cita presencial acordada entre los tutores de dos mascotas
    en un espacio público o parque canino verificado.
    """

    class MeetupStatus(models.TextChoices):
        PROPOSED = 'proposed', _('Propuesto')
        CONFIRMED = 'confirmed', _('Confirmado')
        COMPLETED = 'completed', _('Completado')
        CANCELLED = 'cancelled', _('Cancelado')

    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='meetups',
        verbose_name=_('Solicitud de match asociada'),
    )
    pet1 = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='meetups_as_pet1',
        verbose_name=_('Mascota anfitriona'),
    )
    pet2 = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='meetups_as_pet2',
        verbose_name=_('Mascota invitada'),
    )
    date = models.DateField(
        verbose_name=_('Fecha del encuentro'),
    )
    time = models.TimeField(
        verbose_name=_('Hora del encuentro'),
    )
    location_name = models.CharField(
        max_length=255,
        verbose_name=_('Lugar de encuentro'),
        help_text=_('Ejemplo: Parque España (Zona canina verificada).'),
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Latitud'),
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Longitud'),
    )
    status = models.CharField(
        max_length=20,
        choices=MeetupStatus.choices,
        default=MeetupStatus.PROPOSED,
        verbose_name=_('Estado de la cita'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas del encuentro'),
        help_text=_('Puntos de acuerdo, normas de seguridad o recordatorios.'),
    )

    class Meta:
        verbose_name = _('Encuentro de mascotas')
        verbose_name_plural = _('Encuentros de mascotas')
        ordering = ['-date', '-time']

    def __str__(self):
        return f'Cita entre {self.pet1.name} y {self.pet2.name} el {self.date} ({self.get_status_display()})'
