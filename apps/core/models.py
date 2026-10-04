from django.conf import settings
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


class AuditLog(TimeStampedModel):
    """
    Modelo para el registro de eventos y auditoría de accesos
    del módulo de seguridad del sistema.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Usuario',
        help_text='Usuario asociado al evento de auditoría.',
    )
    action = models.CharField(
        max_length=150,
        verbose_name='Acción',
        help_text='Descripción de la acción o evento auditado.',
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Dirección IP',
        help_text='Dirección IP desde la cual se ejecutó la acción.',
    )
    details = models.TextField(
        blank=True,
        verbose_name='Detalles adicionales',
        help_text='Información complementaria sobre la acción ejecutada.',
    )

    class Meta:
        verbose_name = 'Log de auditoría'
        verbose_name_plural = 'Logs de auditoría'
        ordering = ['-created_at']

    def __str__(self):
        username = self.user.username if self.user else 'Anónimo'
        return f'[{self.created_at:%Y-%m-%d %H:%M}] {username}: {self.action}'
