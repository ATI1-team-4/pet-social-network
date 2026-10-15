"""Controladores de vista para el módulo accounts (autenticación y accesos)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.forms import LoginForm, PasswordResetRequestForm, RegisterForm
from apps.accounts.services import (
    authenticate_by_email_or_username,
    create_tutor_user,
    get_user_profile_context,
    update_user_profile,
)
from apps.accounts.signals import get_client_ip

# ==============================================================================
# Vistas Públicas de Autenticación y Registro
# ==============================================================================


def login_view(request):
    """
    Procesa el inicio de sesión y renderiza la pantalla correspondiente.
    Ruta pública: si el usuario ya está autenticado, redirige al selector de mascota.
    """
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect('pets:pet_select')

    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Autenticar mediante correo electrónico o nombre de usuario
            user = authenticate_by_email_or_username(request, identifier, password)
            if user is not None:
                login(request, user)

                # Configurar caducidad de la cookie de sesión según preferencia
                if remember_me:
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)

                # Redirigir a la URL de destino solicitada si es segura
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)
                return redirect('pets:pet_select')

            # Notificar error de credenciales al usuario
            messages.error(
                request,
                _(
                    'Correo electrónico o contraseña incorrectos. Por favor, verifica tus credenciales.'
                ),
            )
        else:
            messages.error(request, _('Por favor, completa todos los campos requeridos.'))

    return render(request, 'accounts/login.html', {'form': form, 'next_url': next_url})


def register_view(request):
    """
    Procesa el registro de nuevos tutores y renderiza la pantalla correspondiente.
    Ruta pública: asigna automáticamente el rol de Tutor y crea el perfil asociado.
    """
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect('pets:pet_select')

    # Limpiar mensajes acumulados al navegar a registro mediante GET
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for _message in storage:
            pass

    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Obtener dirección IP del cliente para registro en auditoría
            client_ip = get_client_ip(request)

            # Delegar la creación del tutor a la capa de servicios
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

            # Iniciar sesión automáticamente tras el registro
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect('pets:pet_select')

        # Mostrar errores específicos del formulario en el banner de notificaciones
        for _field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')

    return render(request, 'accounts/register.html', {'form': form, 'next_url': next_url})


def password_reset_view(request):
    """
    Procesa la solicitud de recuperación de contraseña.
    Ruta pública: emite el enlace de restablecimiento seguro.
    """
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
    """
    Cierra la sesión activa del usuario y redirige a la página principal.
    Ruta pública: limpia la sesión y los mensajes residuales.
    """
    if request.user.is_authenticated:
        logout(request)

    # Vaciar cualquier mensaje acumulado en la sesión
    storage = messages.get_messages(request)
    for _message in storage:
        pass

    return redirect('core:home')


# ==============================================================================
# Vistas Protegidas de Perfil de Usuario
# ==============================================================================


@login_required
def profile_view(request):
    """
    Renderiza la pantalla oficial de gestión del perfil del tutor autenticado.
    Delega la consulta de mascotas, conexiones y mascota activa a la capa de servicios.
    """
    # Construir el contexto del perfil a través de la capa de servicios
    session_active_pet_id = request.session.get('active_pet_id')
    context = get_user_profile_context(request.user, session_active_pet_id=session_active_pet_id)

    return render(request, 'accounts/user_profile.html', context)


@login_required
@require_POST
def profile_save_view(request):
    """
    Actualiza la información personal, ubicación y avatar del tutor autenticado.
    Delega la persistencia transaccional y el manejo de archivos a la capa de servicios.
    """
    # Delegar la actualización de datos personales y avatar a la capa de servicios
    update_user_profile(request.user, request.POST, request.FILES)

    # Notificar al tutor y redirigir a la vista de perfil
    messages.success(request, _('Tu perfil ha sido actualizado exitosamente.'))
    return redirect('accounts:profile')
