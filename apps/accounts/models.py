import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


def user_avatar_upload_path(instance, filename):
    """
    Genera la ruta de almacenamiento para avatars de tutores siguiendo
    la convención autodescriptiva definida en README.md:
    avatars/user_{user_id}_avatar_{id_unico}.{ext}
    Ejemplo: avatars/user_42_avatar_9f8e7d6c.jpg
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    user_id = instance.user_id or getattr(instance.user, 'id', 'unknown')
    id_unico = uuid.uuid4().hex[:8]
    return f'avatars/user_{user_id}_avatar_{id_unico}.{ext}'





class UserProfile(TimeStampedModel):
    """
    Perfil extendido para tutores y administradores de Petly.
    Almacena información complementaria como documento de identidad, teléfono,
    ubicación geográfica, reputación y afinidades del tutor.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Usuario'),
        help_text=_('Cuenta de usuario vinculada al perfil.'),
    )
    avatar = models.ImageField(
        upload_to=user_avatar_upload_path,
        blank=True,
        null=True,
        verbose_name=_('Avatar'),
        help_text=_('Fotografía o imagen de perfil del usuario.'),
    )
    phone_prefix = models.CharField(
        max_length=6,
        default='+58',
        verbose_name=_('Código de país'),
        help_text=_('Prefijo telefónico internacional.'),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono'),
        help_text=_('Número de teléfono o contacto del tutor.'),
    )
    id_type = models.CharField(
        max_length=2,
        default='V',
        verbose_name=_('Tipo de documento'),
        help_text=_('Nacionalidad o tipo de documento (V, E, J, P).'),
    )
    id_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Número de cédula/documento'),
        help_text=_('Número de identificación legal del tutor.'),
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_('Biografía'),
        help_text=_('Presentación o notas sobre el tutor.'),
    )
    city = models.CharField(
        max_length=100,
        default='Caracas',
        blank=True,
        verbose_name=_('Ciudad'),
        help_text=_('Ciudad o localidad de residencia del tutor.'),
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Latitud'),
        help_text=_('Coordenada geográfica de latitud.'),
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Longitud'),
        help_text=_('Coordenada geográfica de longitud.'),
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de nacimiento'),
        help_text=_('Fecha de nacimiento del tutor.'),
    )
    gender = models.CharField(
        max_length=1,
        choices=[
            ('M', _('Masculino')),
            ('F', _('Femenino')),
            ('O', _('Otro')),
        ],
        blank=True,
        verbose_name=_('Género'),
        help_text=_('Género o identidad del tutor.'),
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.00,
        verbose_name=_('Calificación'),
        help_text=_('Puntuación promedio del tutor (1.00 a 5.00).'),
    )
    completed_meetings_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Citas completadas'),
        help_text=_('Total de citas de socialización o cruza concretadas.'),
    )
    favorite_color = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Color favorito'),
        help_text=_('Color preferido para personalización de perfil.'),
    )
    favorite_book = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Libro favorito'),
        help_text=_('Libro favorito para afinidad cultural.'),
    )
    favorite_music = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Música favorita'),
        help_text=_('Género o banda favorita.'),
    )
    favorite_videogame = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Videojuego favorito'),
        help_text=_('Videojuego preferido.'),
    )

    class Meta:
        verbose_name = _('Perfil de usuario')
        verbose_name_plural = _('Perfiles de usuario')
        constraints = [
            models.UniqueConstraint(
                fields=['id_type', 'id_number'],
                condition=~models.Q(id_number=''),
                name='unique_tutor_identity_document',
            ),
        ]

    def __str__(self):
        full_name = self.user.get_full_name()
        identifier = full_name if full_name else self.user.username
        return f'Perfil de {identifier}'

    @property
    def avatar_url(self):
        """Retorna la URL del avatar del usuario o el fallback neutro estilo WhatsApp."""
        if self.avatar and hasattr(self.avatar, 'name') and self.avatar.name:
            try:
                return self.avatar.url
            except ValueError:
                pass
        return f'{settings.STATIC_URL}images/avatars/default_user.svg'

    @property
    def has_avatar(self):
        return bool(self.avatar and hasattr(self.avatar, 'name') and self.avatar.name)


class UserReport(TimeStampedModel):
    """
    Reportes emitidos por tutores sobre otros usuarios o mascotas
    por conductas, fotos o contenido inapropiado dentro del feed y solicitudes.
    """

    class ReportStatus(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        REVIEWED = 'reviewed', _('Revisado')
        ACTION_TAKEN = 'action_taken', _('Acción tomada')
        DISMISSED = 'dismissed', _('Descartado')

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_filed',
        verbose_name=_('Reportado por'),
        help_text=_('Usuario tutor que emitió la denuncia.'),
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_received',
        verbose_name=_('Usuario reportado'),
        help_text=_('Usuario denunciado.'),
    )
    reported_pet = models.ForeignKey(
        'pets.Pet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name=_('Mascota reportada'),
        help_text=_('Mascota específica sobre la que recae el reporte, si aplica.'),
    )
    reason = models.TextField(
        verbose_name=_('Motivo del reporte'),
        help_text=_('Explicación detallada de la falta o incidente.'),
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        verbose_name=_('Estado de revisión'),
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name=_('Notas del administrador'),
        help_text=_('Observaciones internas de moderación.'),
    )

    class Meta:
        verbose_name = _('Reporte de usuario')
        verbose_name_plural = _('Reportes de usuarios')
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'Reporte #{self.pk} contra {self.reported_user.username} ({self.get_status_display()})'
        )
