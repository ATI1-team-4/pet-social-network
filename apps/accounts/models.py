from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    """
    Perfil extendido para tutores y administradores de Petly.
    Almacena información complementaria como documento de identidad y teléfono.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Usuario'),
        help_text=_('Cuenta de usuario vinculada al perfil.'),
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
