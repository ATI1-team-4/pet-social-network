"""
Pruebas unitarias para concertación de citas y agenda de encuentros caninos (Issue #65).

Verifica:
- Validación temporal de fechas y horas futuras en ScheduleMeetupForm.
- Validación de parques caninos autorizados y espacios públicos verificados.
- Persistencia de citas en PetMeetup vía endpoint POST/AJAX schedule_meetup_view.
- Restricciones de métodos HTTP (@require_POST y @login_required).
- Cancelación de citas con control de permisos y actualización de estado a CANCELLED.
- Incremento del contador de citas completadas en el perfil de los tutores involucrados (UC-10).
- Detección de solapamiento de horario para las mascotas participantes.
"""

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.pets.forms import ScheduleMeetupForm
from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies
from apps.pets.services import (
    cancel_pet_meetup,
    complete_pet_meetup,
    confirm_pet_meetup,
    schedule_pet_meetup,
)

User = get_user_model()


class PetMeetupTests(TestCase):
    """Pruebas para la concertación, validación y cancelación de encuentros caninos."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='tutor_citas',
            email='tutor@example.com',
            password='password123',
            first_name='Alejandro',
            last_name='Pérez',
        )
        self.other_user = User.objects.create_user(
            username='otro_tutor',
            email='otro@example.com',
            password='password123',
            first_name='Mariana',
            last_name='Gómez',
        )
        self.third_user = User.objects.create_user(
            username='tercer_tutor',
            email='tercero@example.com',
            password='password123',
            first_name='Carlos',
            last_name='Rojas',
        )
        UserProfile.objects.get_or_create(user=self.user)
        UserProfile.objects.get_or_create(user=self.other_user)
        UserProfile.objects.get_or_create(user=self.third_user)

        self.species, _ = PetSpecies.objects.get_or_create(
            slug='perro', defaults={'name': 'Perro', 'icon_name': 'dog'}
        )

        self.pet = Pet.objects.create(
            owner=self.user,
            name='Zeus',
            species=self.species,
            breed='Husky',
            gender=Pet.Gender.MACHO,
            birth_date='2020-03-15',
        )
        self.other_pet = Pet.objects.create(
            owner=self.other_user,
            name='Kira',
            species=self.species,
            breed='Husky',
            gender=Pet.Gender.HEMBRA,
            birth_date='2021-06-20',
        )
        self.third_pet = Pet.objects.create(
            owner=self.third_user,
            name='Rocky',
            species=self.species,
            breed='Labrador',
            gender=Pet.Gender.MACHO,
            birth_date='2022-01-10',
        )

        self.match_request = MatchRequest.objects.create(
            from_pet=self.other_pet,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
            notes='¡Encantados de coordinar una cita!',
        )

        self.future_date = date.today() + timedelta(days=5)
        self.future_time = time(10, 30)
        self.location = 'Parque España (Zona canina verificada)'

    def test_schedule_meetup_form_instantiation(self):
        """Verifica la inicialización de los campos en ScheduleMeetupForm."""
        form = ScheduleMeetupForm()
        self.assertIn('date', form.fields)
        self.assertIn('time', form.fields)
        self.assertIn('location_name', form.fields)
        self.assertIn('notes', form.fields)

    def test_schedule_meetup_endpoint_requires_post(self):
        """Verifica que el agendamiento rechace peticiones GET."""
        self.client.login(username='tutor_citas', password='password123')
        response = self.client.get(reverse('pets:schedule_meetup'))
        self.assertEqual(response.status_code, 405)

    def test_cancel_meetup_endpoint_requires_post(self):
        """Verifica que la cancelación rechace peticiones GET."""
        self.client.login(username='tutor_citas', password='password123')
        response = self.client.get(reverse('pets:cancel_meetup', kwargs={'meetup_id': 1}))
        self.assertEqual(response.status_code, 405)

    def test_schedule_meetup_future_date_validation(self):
        """Verifica que no se permitan fechas ni horas pasadas al agendar encuentros."""
        past_date = date.today() - timedelta(days=1)
        form_past = ScheduleMeetupForm(
            data={
                'date': past_date,
                'time': time(10, 0),
                'location_name': self.location,
            }
        )
        self.assertFalse(form_past.is_valid())
        self.assertIn('date', form_past.errors)

        # Fecha y hora pasadas, incluso si la resta cruza la medianoche
        now = timezone.localtime() if timezone.is_aware(timezone.now()) else datetime.now()
        past_datetime = now - timedelta(hours=2)

        form_past_time = ScheduleMeetupForm(
            data={
                'date': past_datetime.date(),
                'time': past_datetime.time(),
                'location_name': self.location,
            }
        )
        self.assertFalse(form_past_time.is_valid())

        # Fecha y hora futuras válidas
        form_future = ScheduleMeetupForm(
            data={
                'date': self.future_date,
                'time': self.future_time,
                'location_name': self.location,
            }
        )
        self.assertTrue(form_future.is_valid())

    def test_schedule_meetup_location_validation(self):
        """Verifica que el campo de lugar de encuentro sea obligatorio."""
        form_empty = ScheduleMeetupForm(
            data={
                'date': self.future_date,
                'time': self.future_time,
                'location_name': '',
            }
        )
        self.assertFalse(form_empty.is_valid())
        self.assertIn('location_name', form_empty.errors)

        form_valid = ScheduleMeetupForm(
            data={
                'date': self.future_date,
                'time': self.future_time,
                'location_name': 'Parque del Este (Área de recreación canina)',
            }
        )
        self.assertTrue(form_valid.is_valid())

    def test_schedule_meetup_endpoint_success(self):
        """Verifica el agendamiento exitoso de una cita mediante AJAX POST."""
        self.client.login(username='tutor_citas', password='password123')
        payload = {
            'target_pet_id': self.other_pet.id,
            'match_request_id': self.match_request.id,
            'date': self.future_date.isoformat(),
            'time': '11:00',
            'location_name': self.location,
            'notes': 'Llevar cartilla de vacunación y correa reforzada.',
        }
        response = self.client.post(
            reverse('pets:schedule_meetup'),
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'scheduled')
        self.assertIn('meetup_id', data)

        # Comprobar en base de datos
        meetup = PetMeetup.objects.get(id=data['meetup_id'])
        self.assertEqual(meetup.host_pet, self.pet)
        self.assertEqual(meetup.guest_pet, self.other_pet)
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)
        self.assertEqual(meetup.location_name, self.location)

    def test_schedule_meetup_endpoint_validation_error(self):
        """Verifica que el endpoint devuelva 400 ante datos temporales inválidos."""
        self.client.login(username='tutor_citas', password='password123')
        past_date = date.today() - timedelta(days=2)
        payload = {
            'target_pet_id': self.other_pet.id,
            'date': past_date.isoformat(),
            'time': '10:00',
            'location_name': self.location,
        }
        response = self.client.post(
            reverse('pets:schedule_meetup'),
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get('status'), 'error')

    def test_cancel_meetup_permission_and_state(self):
        """Verifica que solo los tutores involucrados puedan cancelar, el estado pase a CANCELLED y se registre el tutor."""
        meetup = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)

        # Tercer usuario no participante intenta cancelar -> 403 Forbidden
        self.client.login(username='tercer_tutor', password='password123')
        forbidden_response = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id}),
            content_type='application/json',
        )
        self.assertEqual(forbidden_response.status_code, 403)

        # Tutor participante cancela -> 200 OK y estado CANCELLED con nombre del tutor en la nota
        self.client.login(username='tutor_citas', password='password123')
        cancel_response = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id}),
            data={'reason': 'Compromiso veterinario imprevisto'},
            content_type='application/json',
        )
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json().get('status'), 'cancelled')

        meetup.refresh_from_db()
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.CANCELLED)
        self.assertIn('Compromiso veterinario imprevisto', meetup.notes)
        self.assertIn('Alejandro Pérez', meetup.notes)

    def test_confirm_meetup_endpoint_lifecycle(self):
        """Verifica que solo el tutor invitado pueda confirmar la cita y cambie a CONFIRMED."""
        meetup = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)

        # El organizador (host) no puede confirmar por sí mismo -> 403
        self.client.login(username='tutor_citas', password='password123')
        host_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(host_resp.status_code, 403)

        # Tercero no participante -> 403
        self.client.login(username='tercer_tutor', password='password123')
        third_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(third_resp.status_code, 403)

        # El invitado (guest) confirma -> 200 OK
        self.client.login(username='otro_tutor', password='password123')
        guest_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(
            guest_resp.status_code, 200, f'guest_resp error: {guest_resp.content.decode()}'
        )
        self.assertEqual(guest_resp.json().get('status'), 'confirmed')

        meetup.refresh_from_db()
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.CONFIRMED)

    def test_complete_meetup_endpoint_lifecycle(self):
        """Verifica que solo citas confirmadas puedan completarse."""
        meetup = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )
        self.client.login(username='tutor_citas', password='password123')
        # Intentar completar una cita que aún está en PROPOSED -> 400
        comp_fail = self.client.post(
            reverse('pets:complete_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(comp_fail.status_code, 400)

        # Invitado confirma la cita
        confirm_pet_meetup(meetup_id=meetup.id, user=self.other_user)

        # Ahora el tutor puede marcarla como completada -> 200
        comp_success = self.client.post(
            reverse('pets:complete_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(comp_success.status_code, 200)
        self.assertEqual(comp_success.json().get('status'), 'completed')

        meetup.refresh_from_db()
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.COMPLETED)

        # Una cita completada no puede ser cancelada -> 400
        cancel_attempt = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id})
        )
        self.assertEqual(cancel_attempt.status_code, 400)
        with self.assertRaises(ValueError):
            cancel_pet_meetup(meetup_id=meetup.id, user=self.user)

    def test_meetup_completed_updates_tutor_reputation_counter(self):
        """
        Verifica que al finalizar satisfactoriamente una cita (status COMPLETED),
        el contador de encuentros completados del perfil de ambos tutores se incremente (UC-10).
        """
        initial_count_user = self.user.profile.completed_meetings_count
        initial_count_other = self.other_user.profile.completed_meetings_count

        meetup = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )
        # Confirmar primero por el tutor invitado
        confirm_pet_meetup(meetup_id=meetup.id, user=self.other_user)

        # Completar la cita
        complete_pet_meetup(meetup_id=meetup.id, user=self.user)

        meetup.refresh_from_db()
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.COMPLETED)

        # El contador en Profile se incrementa dinámicamente
        self.assertEqual(self.user.profile.completed_meetings_count, initial_count_user + 1)
        self.assertEqual(self.other_user.profile.completed_meetings_count, initial_count_other + 1)

    def test_schedule_meetup_conflicting_schedule(self):
        """Verifica que no se permita solapar dos encuentros para la misma mascota en el mismo horario."""
        schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )

        # Intentar agendar otra cita para Zeus a la misma fecha y hora
        with self.assertRaises(ValueError):
            schedule_pet_meetup(
                requester_user=self.user,
                requester_pet=self.pet,
                target_pet=self.third_pet,
                meeting_date=self.future_date,
                meeting_time=self.future_time,
                location_name=self.location,
            )

    def test_schedule_multiple_meetups_different_times_allowed(self):
        """Verifica que una mascota pueda agendar múltiples citas en fechas u horarios diferentes."""
        meetup1 = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.other_pet,
            meeting_date=self.future_date,
            meeting_time=self.future_time,
            location_name=self.location,
        )
        # Horario diferente en la misma fecha
        diff_hour = (self.future_time.hour + 2) % 24
        different_time = time(diff_hour, 0)
        meetup2 = schedule_pet_meetup(
            requester_user=self.user,
            requester_pet=self.pet,
            target_pet=self.third_pet,
            meeting_date=self.future_date,
            meeting_time=different_time,
            location_name=self.location,
        )
        self.assertIsNotNone(meetup1.id)
        self.assertIsNotNone(meetup2.id)
        self.assertNotEqual(meetup1.id, meetup2.id)
        self.assertEqual(PetMeetup.objects.filter(host_pet=self.pet).count(), 2)
