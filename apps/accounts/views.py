"""Controladores de vista para el módulo accounts (autenticación y accesos)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.forms import LoginForm, PasswordResetRequestForm, RegisterForm
from apps.accounts.models import UserProfile
from apps.accounts.services import (
    authenticate_by_email_or_username,
    create_tutor_user,
)
from apps.accounts.signals import get_client_ip
from apps.pets.models import MatchRequest


def login_view(request):
    """Procesa el inicio de sesión y renderiza la pantalla correspondiente."""
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

            user = authenticate_by_email_or_username(request, identifier, password)
            if user is not None:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 semanas de sesión
                else:
                    request.session.set_expiry(0)  # Expira al cerrar el navegador

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

    return render(request, 'accounts/login.html', {'form': form, 'next_url': next_url})


def register_view(request):
    """Procesa el registro de nuevos tutores y renderiza la pantalla correspondiente."""
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
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

            # Iniciar sesión automáticamente tras el registro y redirigir a selección de mascota o next
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect('pets:pet_select')

        # Mostrar errores específicos del formulario en el banner de mensajes
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')

    return render(request, 'accounts/register.html', {'form': form, 'next_url': next_url})


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
    Carga las mascotas reales del usuario, el total de conexiones y la mascota activa.
    """
    user = request.user
    user_pets = user.pets.select_related('species').all()
    pets_count = user_pets.count()

    # Conexiones activas: Solicitudes de match aceptadas donde intervenga alguna mascota del tutor
    active_connections_count = MatchRequest.objects.filter(
        Q(from_pet__in=user_pets) | Q(to_pet__in=user_pets),
        status=MatchRequest.RequestStatus.ACCEPTED,
    ).count()

    # Mascota activa en búsqueda:
    # 1) Mascota activa seleccionada en sesión (active_pet_id)
    # 2) O primera mascota con is_active_for_match=True
    # 3) O primera mascota del tutor
    active_pet = None
    active_pet_id = request.session.get('active_pet_id')
    if active_pet_id and str(active_pet_id).isdigit():
        active_pet = user_pets.filter(id=int(active_pet_id)).first()

    if not active_pet:
        active_pet = user_pets.filter(is_active_for_match=True).first() or user_pets.first()

    context = {
        'user_pets': user_pets,
        'pets_count': pets_count,
        'active_connections_count': active_connections_count,
        'active_pet': active_pet,
    }
    return render(request, 'accounts/user_profile.html', context)


@login_required
@require_POST
def profile_save_view(request):
    """
    Actualiza la información personal y el avatar del tutor autenticado.
    Almacena las fotografías subidas en media/avatars/ según la convención del proyecto.
    """
    user = request.user
    profile, _created = UserProfile.objects.get_or_create(user=user)

    full_name = request.POST.get('full_name', '').strip()
    if full_name:
        parts = full_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.save()

    email = request.POST.get('email', '').strip()
    if email:
        user.email = email
        user.save()

    profile.phone_number = request.POST.get('phone', profile.phone_number).strip()
    profile.state = request.POST.get('state', profile.state).strip()
    profile.municipality = request.POST.get('municipality', profile.municipality).strip()
    profile.neighborhood = request.POST.get('neighborhood', profile.neighborhood).strip()
    if 'city' in request.POST and not request.POST.get('municipality'):
        profile.municipality = request.POST.get('city', '').strip()

    if 'latitude' in request.POST:
        lat_val = request.POST.get('latitude', '').strip()
        if lat_val:
            try:
                profile.latitude = float(lat_val)
            except ValueError:
                pass
        else:
            profile.latitude = None

    if 'longitude' in request.POST:
        lon_val = request.POST.get('longitude', '').strip()
        if lon_val:
            try:
                profile.longitude = float(lon_val)
            except ValueError:
                pass
        else:
            profile.longitude = None

    birth_date_val = request.POST.get('birth_date', '').strip()
    if birth_date_val:
        try:
            profile.birth_date = birth_date_val
        except (ValueError, TypeError):
            pass

    gender_val = request.POST.get('gender', '').strip()
    if gender_val:
        profile.gender = (
            'F'
            if gender_val in ('Femenino', 'F', 'f')
            else ('M' if gender_val in ('Masculino', 'M', 'm') else 'O')
        )

    profile.favorite_color = request.POST.get('favorite_color', profile.favorite_color).strip()
    profile.favorite_book = request.POST.get('favorite_book', profile.favorite_book).strip()
    profile.favorite_music = request.POST.get('favorite_music', profile.favorite_music).strip()
    profile.favorite_videogame = request.POST.get(
        'favorite_game', profile.favorite_videogame
    ).strip()

    if request.POST.get('remove_avatar') == 'true' and profile.avatar:
        profile.avatar.delete(save=False)
        profile.avatar = None

    if 'avatar' in request.FILES:
        profile.avatar = request.FILES['avatar']

    profile.save()
    messages.success(request, _('Tu perfil ha sido actualizado exitosamente.'))
    return redirect('accounts:profile')
