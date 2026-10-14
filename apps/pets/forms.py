"""Formularios para el módulo de mascotas y encuentros."""

from datetime import date, datetime

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.pets.models import PetMeetup

# Parques caninos y espacios públicos autorizados y verificados
AUTHORIZED_CANINE_PARKS = [
    'Parque España (Zona canina verificada)',
    'Parque España (Zona Canina Verificada)',
    'Parque del Este (Área de recreación canina)',
    'Parque Vizcaya (Espacio cercado)',
    'Parque La Rosaleda (Los Teques)',
    'Parque Los Caobos (Zona canina)',
]


class ScheduleMeetupForm(forms.ModelForm):
    """
    Formulario para concertación de citas y encuentros caninos seguros (Issue #65).

    Valida:
    - Fechas y horas estrictamente futuras.
    - Parques caninos autorizados o espacios públicos verificados.
    - Indicaciones o notas sanitarias para el encuentro.
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

    def clean_location_name(self):
        """Valida que el lugar corresponda a un parque canino autorizado o espacio verificado."""
        location_name = self.cleaned_data.get('location_name', '').strip()
        if not location_name:
            raise forms.ValidationError(_('Debe ingresar un lugar de encuentro canino verificado.'))

        authorized_normalized = [p.lower() for p in AUTHORIZED_CANINE_PARKS]
        loc_lower = location_name.lower()

        is_authorized = (
            loc_lower in authorized_normalized
            or any(
                p in loc_lower
                for p in [
                    'parque españa',
                    'parque del este',
                    'parque vizcaya',
                    'la rosaleda',
                    'los caobos',
                    'zona canina verificada',
                    'área de recreación canina',
                    'espacio cercado',
                ]
            )
        )

        if not is_authorized:
            raise forms.ValidationError(
                _('El lugar seleccionado no corresponde a un parque canino autorizado o espacio público verificado.')
            )

        return location_name

    def clean_date(self):
        """Valida que la fecha seleccionada no sea en el pasado."""
        meeting_date = self.cleaned_data.get('date')
        if not meeting_date:
            raise forms.ValidationError(_('Debe especificar la fecha de la cita.'))
        today = timezone.localdate() if timezone.is_aware(timezone.now()) else date.today()
        if meeting_date < today:
            raise forms.ValidationError(_('La fecha del encuentro no puede ser en el pasado.'))
        return meeting_date

    def clean(self):
        """Valida disponibilidad y combinación de fecha/hora en el futuro."""
        cleaned_data = super().clean()
        meeting_date = cleaned_data.get('date')
        meeting_time = cleaned_data.get('time')

        if meeting_date and meeting_time:
            now = timezone.localtime() if timezone.is_aware(timezone.now()) else datetime.now()
            meeting_dt = datetime.combine(meeting_date, meeting_time)
            if timezone.is_aware(now):
                meeting_dt = timezone.make_aware(meeting_dt, timezone.get_current_timezone())
            if meeting_dt <= now:
                raise forms.ValidationError(
                    _('La fecha y hora propuestas deben corresponder a un momento futuro.')
                )
        return cleaned_data

