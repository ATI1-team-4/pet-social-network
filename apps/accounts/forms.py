"""Formularios de validación y entrada de datos para el módulo accounts."""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import UserProfile

User = get_user_model()


class LoginForm(forms.Form):
    """Formulario para inicio de sesión de usuarios."""

    email = forms.CharField(
        label=_('Correo electrónico o usuario'),
        widget=forms.TextInput(
            attrs={'placeholder': 'edwyn@petly.com', 'autocomplete': 'username'}
        ),
    )
    password = forms.CharField(
        label=_('Contraseña'),
        widget=forms.PasswordInput(
            attrs={'placeholder': '••••••••••••', 'autocomplete': 'current-password'}
        ),
    )
    remember_me = forms.BooleanField(
        required=False,
        label=_('Recordar mi sesión'),
    )


class RegisterForm(forms.Form):
    """Formulario para registro de nuevos tutores en Petly."""

    full_name = forms.CharField(
        label=_('Nombre completo'),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Stefany Martínez'}),
    )
    email = forms.EmailField(
        label=_('Correo electrónico'),
        widget=forms.EmailInput(attrs={'placeholder': 'stefany@petly.com'}),
    )
    phone_prefix = forms.CharField(
        label=_('Código de país'),
        max_length=6,
        initial='+58',
        required=False,
    )
    phone = forms.CharField(
        label=_('Teléfono / contacto'),
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '424 123 4567'}),
    )
    id_type = forms.CharField(
        label=_('Tipo de documento'),
        max_length=2,
        initial='V',
        required=False,
    )
    id_number = forms.CharField(
        label=_('Cédula'),
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '27456789'}),
    )
    password = forms.CharField(
        label=_('Contraseña'),
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••••••'}),
    )
    password_confirm = forms.CharField(
        label=_('Confirmar contraseña'),
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••••••'}),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _('Ya existe una cuenta registrada con este correo electrónico.')
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', _('Las contraseñas no coinciden.'))

            # Requisito del prototipo: al menos 8 caracteres y un número
            if not re.search(r'\d', password):
                self.add_error('password', _('La contraseña debe contener al menos un número.'))

        # Validar unicidad y formato del documento de identidad
        id_type = (cleaned_data.get('id_type') or 'V').strip().upper()
        id_number = (cleaned_data.get('id_number') or '').strip()

        if id_number:
            if id_type in ('V', 'E') and not id_number.isdigit():
                self.add_error('id_number', _('La cédula debe contener únicamente números.'))
            elif UserProfile.objects.filter(id_type=id_type, id_number=id_number).exists():
                self.add_error(
                    'id_number',
                    _('Ya existe una cuenta registrada con este documento de identidad (%(type)s-%(number)s).')
                    % {'type': id_type, 'number': id_number},
                )

        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    """Formulario para solicitar restablecimiento de contraseña."""

    email = forms.EmailField(
        label=_('Correo electrónico registrado'),
        widget=forms.EmailInput(attrs={'placeholder': 'bryan@petly.com'}),
    )
