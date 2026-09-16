from django.db import models


class TimeStampedModel(models.Model):
    """
    Modelo base abstracto que provee campos de auditoría temporal
    (creación y última modificación) para rastreo de registros.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
        help_text='Momento exacto en el que se creó el registro.',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización',
        help_text='Momento de la última modificación del registro.',
    )

    class Meta:
        abstract = True
