"""Formularios para el módulo de mascotas y encuentros."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.pets.models import PetMeetup


class ScheduleMeetupForm(forms.ModelForm):
    """
    Silueta del formulario para concertación de citas y encuentros caninos seguros (Issue #65).

    El equipo debe implementar:
    - Validación de fechas y horas futuras (evitar fechas pasadas o fuera de horario permitido).
    - Validación del parque canino autorizado o espacio público verificado.
    - Manejo de notas adicionales y precauciones sanitarias mutuas.
    """

    class Meta:
        model = PetMeetup
        fields = [
            'date',
            'time',
            'location_name',
            'notes',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-petly'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'input-petly'}),
            'location_name': forms.TextInput(
                attrs={'class': 'input-petly', 'placeholder': _('Nombre del parque o plaza')}
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'input-petly',
                    'rows': 3,
                    'placeholder': _('Indicaciones o temperamento a considerar'),
                }
            ),
        }

    def clean_date(self):
        """Silueta: Valida que la fecha seleccionada sea hoy o futura."""
        meeting_date = self.cleaned_data.get('date')
        # TODO: Implementar validación de fecha futura
        return meeting_date

    def clean(self):
        """Silueta: Valida disponibilidad y combinación de fecha/hora."""
        cleaned_data = super().clean()
        # TODO: Implementar validación integral de fecha y hora futura
        return cleaned_data
