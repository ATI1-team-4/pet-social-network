"""
Pruebas unitarias para concertación de citas y agenda de encuentros caninos.

Verifica:
- Validación temporal de fechas y horas futuras en ScheduleMeetupForm.
- Validación de lugares y espacios públicos para los encuentros.
- Persistencia de citas en PetMeetup mediante el endpoint schedule_meetup.
- Restricciones de métodos HTTP (POST requerido y autenticación obligatoria).
- Cancelación de citas con control de permisos y actualización de estado.
- Incremento del contador de citas completadas en el perfil de los tutores.
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
        # Obtenemos los usuarios correspondientes a los desarrolladores del equipo
        self.user = User.objects.get(username='edwyn')
        self.other_user = User.objects.get(username='stefany')
        self.third_user = User.objects.get(username='bryan')

        # Aseguramos que los perfiles de usuario existan en la base de datos de pruebas
        UserProfile.objects.get_or_create(user=self.user)
        UserProfile.objects.get_or_create(user=self.other_user)
        UserProfile.objects.get_or_create(user=self.third_user)

        self.species, _ = PetSpecies.objects.get_or_create(
            slug='perro', defaults={'name': 'Perro', 'icon_name': 'dog'}
        )

        # Registramos las mascotas vinculadas a cada desarrollador
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

        # Creamos una solicitud de match previamente aceptada entre ambas mascotas
        self.match_request = MatchRequest.objects.create(
            from_pet=self.other_pet,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
            notes='¡Encantados de coordinar una cita!',
        )

        # Definimos una fecha y hora futura válida para agendar los encuentros
        self.future_date = date.today() + timedelta(days=5)
        self.future_time = time(10, 30)
        self.location = 'Parque España (Zona canina verificada)'

    def test_schedule_meetup_form_instantiation(self):
        """Verifica la inicialización de los campos en ScheduleMeetupForm."""
        form = ScheduleMeetupForm()
        # Verificamos que cada campo esperado esté presente en el diccionario de campos del formulario
        self.assertIn('date', form.fields)
        self.assertIn('time', form.fields)
        self.assertIn('location_name', form.fields)
        self.assertIn('notes', form.fields)

    def test_schedule_meetup_endpoint_requires_post(self):
        """Verifica que el agendamiento rechace peticiones GET."""
        self.client.login(username='edwyn', password='123456789')
        response = self.client.get(reverse('pets:schedule_meetup'))
        # Comprobamos que el servidor devuelva código HTTP 405 (método no permitido) al recibir GET
        self.assertEqual(response.status_code, 405)

    def test_cancel_meetup_endpoint_requires_post(self):
        """Verifica que la cancelación rechace peticiones GET."""
        self.client.login(username='edwyn', password='123456789')
        response = self.client.get(reverse('pets:cancel_meetup', kwargs={'meetup_id': 1}))
        # Comprobamos que el servidor devuelva código HTTP 405 (método no permitido)
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
        # Comprobamos que el formulario sea inválido ante una fecha anterior a hoy
        self.assertFalse(form_past.is_valid())
        # Verificamos que el error se concentre en el campo de fecha ('date')
        self.assertIn('date', form_past.errors)

        # Evaluamos con una hora que ya transcurrió en el día de hoy
        now = timezone.localtime() if timezone.is_aware(timezone.now()) else datetime.now()
        past_datetime = now - timedelta(hours=2)

        form_past_time = ScheduleMeetupForm(
            data={
                'date': past_datetime.date(),
                'time': past_datetime.time(),
                'location_name': self.location,
            }
        )
        # Comprobamos que rechace horas que ya pasaron
        self.assertFalse(form_past_time.is_valid())

        # Evaluamos con una fecha y hora futuras plenamente válidas
        form_future = ScheduleMeetupForm(
            data={
                'date': self.future_date,
                'time': self.future_time,
                'location_name': self.location,
            }
        )
        # Verificamos que el formulario apruebe la validación con éxito
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
        # Comprobamos que no sea válido al dejar el lugar vacío
        self.assertFalse(form_empty.is_valid())
        # Verificamos que el error reportado corresponda a 'location_name'
        self.assertIn('location_name', form_empty.errors)

        form_valid = ScheduleMeetupForm(
            data={
                'date': self.future_date,
                'time': self.future_time,
                'location_name': 'Parque del Este (Área de recreación canina)',
            }
        )
        # Comprobamos que el formulario sea aceptado cuando se especifica un lugar
        self.assertTrue(form_valid.is_valid())

    def test_schedule_meetup_endpoint_success(self):
        """Verifica el agendamiento exitoso de una cita mediante AJAX POST."""
        self.client.login(username='edwyn', password='123456789')
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
        # Verificamos que la respuesta HTTP sea 200 (éxito)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Comprobamos que el estado devuelto en el JSON sea 'scheduled'
        self.assertEqual(data.get('status'), 'scheduled')
        # Verificamos que el JSON devuelva la clave 'meetup_id'
        self.assertIn('meetup_id', data)

        # Comprobamos la persistencia del registro en la base de datos
        meetup = PetMeetup.objects.get(id=data['meetup_id'])
        self.assertEqual(meetup.host_pet, self.pet)
        self.assertEqual(meetup.guest_pet, self.other_pet)
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)
        self.assertEqual(meetup.location_name, self.location)

    def test_schedule_meetup_endpoint_validation_error(self):
        """Verifica que el endpoint devuelva 400 ante datos temporales inválidos."""
        self.client.login(username='edwyn', password='123456789')
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
        # Verificamos que el endpoint devuelva código HTTP 400 (solicitud incorrecta)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        # Comprobamos que el estado en la respuesta JSON sea 'error'
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
        # Comprobamos que la cita inicie en estado propuesto (PROPOSED)
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)

        # Intentamos cancelar con un tercer usuario que no participa en el encuentro (Bryan)
        self.client.login(username='bryan', password='123456789')
        forbidden_response = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id}),
            content_type='application/json',
        )
        # Verificamos que el servidor deniegue la acción con código HTTP 403 (prohibido)
        self.assertEqual(forbidden_response.status_code, 403)

        # El tutor participante (Edwyn) procede a cancelar el encuentro
        self.client.login(username='edwyn', password='123456789')
        cancel_response = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id}),
            data={'reason': 'Compromiso veterinario imprevisto'},
            content_type='application/json',
        )
        # Verificamos que la cancelación responda con código HTTP 200 (éxito)
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json().get('status'), 'cancelled')

        # Recargamos la cita de la base de datos para inspeccionar su nuevo estado
        meetup.refresh_from_db()
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.CANCELLED)
        # Verificamos que el motivo de la cancelación y el nombre del tutor figuren en las notas
        self.assertIn('Compromiso veterinario imprevisto', meetup.notes)
        self.assertIn('Edwyn Guzmán', meetup.notes)

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
        # Comprobamos el estado inicial en propuesta
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.PROPOSED)

        # El organizador no puede auto-confirmar su propia propuesta
        self.client.login(username='edwyn', password='123456789')
        host_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Verificamos que el servidor devuelva código HTTP 403 (prohibido)
        self.assertEqual(host_resp.status_code, 403)

        # Un usuario externo que no participa tampoco puede confirmar
        self.client.login(username='bryan', password='123456789')
        third_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Verificamos que devuelva código HTTP 403 (prohibido)
        self.assertEqual(third_resp.status_code, 403)

        # La tutora invitada (Stefany) confirma la propuesta de cita
        self.client.login(username='stefany', password='123456789')
        guest_resp = self.client.post(
            reverse('pets:confirm_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Verificamos que la confirmación sea exitosa con código HTTP 200
        self.assertEqual(guest_resp.status_code, 200)
        self.assertEqual(guest_resp.json().get('status'), 'confirmed')

        # Recargamos el encuentro desde la base de datos
        meetup.refresh_from_db()
        # Comprobamos que el estado se haya actualizado a CONFIRMED
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
        self.client.login(username='edwyn', password='123456789')
        # Intentamos completar la cita cuando aún se encuentra en estado PROPOSED
        comp_fail = self.client.post(
            reverse('pets:complete_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Verificamos que devuelva código HTTP 400 (solicitud inválida por estado incorrecto)
        self.assertEqual(comp_fail.status_code, 400)

        # La tutora invitada procede a confirmar el encuentro
        confirm_pet_meetup(meetup_id=meetup.id, user=self.other_user)

        # Ahora el tutor organizador completa el encuentro
        comp_success = self.client.post(
            reverse('pets:complete_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Verificamos que la finalización sea exitosa con código HTTP 200
        self.assertEqual(comp_success.status_code, 200)
        self.assertEqual(comp_success.json().get('status'), 'completed')

        meetup.refresh_from_db()
        # Comprobamos que el estado en la base de datos sea COMPLETED
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.COMPLETED)

        # Verificamos que una cita completada ya no pueda cancelarse
        cancel_attempt = self.client.post(
            reverse('pets:cancel_meetup', kwargs={'meetup_id': meetup.id})
        )
        # Comprobamos que el intento de cancelación retorne código HTTP 400
        self.assertEqual(cancel_attempt.status_code, 400)
        # Verificamos que el servicio lance ValueError al intentar cancelar una cita completada
        with self.assertRaises(ValueError):
            cancel_pet_meetup(meetup_id=meetup.id, user=self.user)

    def test_meetup_completed_updates_tutor_reputation_counter(self):
        """Verifica que al finalizar satisfactoriamente una cita el contador de encuentros de ambos tutores aumente."""
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
        # El tutor invitado confirma la cita
        confirm_pet_meetup(meetup_id=meetup.id, user=self.other_user)

        # El tutor anfitrión marca la cita como completada
        complete_pet_meetup(meetup_id=meetup.id, user=self.user)

        meetup.refresh_from_db()
        # Comprobamos que el estado de la cita sea COMPLETED
        self.assertEqual(meetup.status, PetMeetup.MeetupStatus.COMPLETED)

        # Comprobamos que el contador de citas completadas se incremente en 1 para ambos tutores
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

        # Verificamos que el servicio lance ValueError si se intenta agendar otra cita para Zeus a la misma hora
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
        # Calculamos un horario diferente para la segunda cita en el mismo día
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
        # Verificamos que ambas citas hayan sido creadas con identificadores únicos
        self.assertIsNotNone(meetup1.id)
        self.assertIsNotNone(meetup2.id)
        self.assertNotEqual(meetup1.id, meetup2.id)
        # Comprobamos que el total de citas activas del anfitrión sea exactamente 2
        self.assertEqual(PetMeetup.objects.filter(host_pet=self.pet).count(), 2)
