"""Controladores de vista para el módulo accounts (autenticación y accesos)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from apps.accounts.forms import LoginForm, PasswordResetRequestForm, RegisterForm
from apps.accounts.services import (
    authenticate_by_email_or_username,
    create_tutor_user,
)
from apps.accounts.signals import get_client_ip


def login_view(request):
    """Procesa el inicio de sesión y renderiza la pantalla correspondiente."""
    if request.user.is_authenticated:
        return redirect('pets:pet_select')

    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            user = authenticate_by_email_or_username(request, identifier, password)
            if user is not None:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 semanas de sesión
                else:
                    request.session.set_expiry(0)  # Expira al cerrar el navegador

                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)
                return redirect('pets:pet_select')

            messages.error(
                request,
                _(
                    'Correo electrónico o contraseña incorrectos. Por favor, verifica tus credenciales.'
                ),
            )
        else:
            messages.error(request, _('Por favor, completa todos los campos requeridos.'))

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    """Procesa el registro de nuevos tutores y renderiza la pantalla correspondiente."""
    if request.user.is_authenticated:
        return redirect('pets:pet_select')

    # Garantizar que al ingresar a la pantalla de registro no se arrastren mensajes previos
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for msg in storage:
            pass

    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            client_ip = get_client_ip(request)
            user = create_tutor_user(
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                phone_prefix=form.cleaned_data.get('phone_prefix', '+58'),
                phone=form.cleaned_data['phone'],
                id_type=form.cleaned_data.get('id_type', 'V'),
                id_number=form.cleaned_data['id_number'],
                ip_address=client_ip,
            )

            # Iniciar sesión automáticamente tras el registro y redirigir a selección de mascota
            login(request, user)
            return redirect('pets:pet_select')

        # Mostrar errores específicos del formulario en el banner de mensajes
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')

    return render(request, 'accounts/register.html', {'form': form})


def password_reset_view(request):
    """Procesa la solicitud de recuperación de contraseña."""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            messages.success(
                request,
                _(
                    'Si el correo %(email)s está registrado, te hemos enviado un enlace seguro para restablecer tu acceso.'
                )
                % {'email': email},
            )
            return redirect('accounts:login')

        messages.error(
            request,
            _('Por favor, ingresa un correo electrónico válido para continuar.'),
        )

    return render(request, 'accounts/password_reset.html')


def logout_view(request):
    """Cierra la sesión activa del usuario y redirige al inicio."""
    if request.user.is_authenticated:
        logout(request)
    # Limpiar cualquier mensaje residual para que no persista en cookies ni viaje a otras rutas
    storage = messages.get_messages(request)
    for msg in storage:
        pass
    return redirect('core:home')


@login_required
def profile_view(request):
    """
    Renderiza la pantalla oficial de Gestión de usuario.
    Requiere que el tutor esté autenticado en el sistema.
    """
    return render(request, 'accounts/user_profile.html')
