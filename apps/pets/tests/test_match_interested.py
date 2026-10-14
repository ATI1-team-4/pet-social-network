"""
Pruebas unitarias para la bandeja de interesados y solicitudes de emparejamiento (Issue #64).

Verifica:
- Consulta ORM de solicitudes recibidas y enviadas vinculadas a la mascota activa.
- Cálculo dinámico de contadores para pestañas ('all', 'interested', 'sent', 'pending').
- Filtrado por pestañas en la vista de interesados.
- Aceptación de solicitudes de match vía AJAX y transición de estados (pending -> accepted).
- Rechazo o descarte de solicitudes de match vía AJAX y transición (pending -> rejected).
- Registro y actualización de mensaje inicial o nota de contacto (MatchRequest.notes).
- Control de acceso, validación de métodos HTTP (@require_POST) y permisos de tutor.
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.pets.models import MatchRequest, Pet, PetSpecies
from apps.pets.services import (
    get_all_match_requests_for_pet,
    get_interested_match_requests,
    get_requests_tab_counters,
    get_sent_match_requests,
)

User = get_user_model()


class MatchInterestedTests(TestCase):
    """Pruebas integrales de la bandeja de interesados y solicitudes."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='tutor_interesados',
            email='tutor@test.com',
            password='password123',
            first_name='Carlos',
            last_name='Gómez',
        )
        self.other_user = User.objects.create_user(
            username='otro_tutor',
            email='otro@test.com',
            password='password123',
            first_name='Mariana',
            last_name='Ríos',
        )
        self.third_user = User.objects.create_user(
            username='tercer_tutor',
            email='tercer@test.com',
            password='password123',
            first_name='Sofía',
            last_name='Castro',
        )

        self.species = PetSpecies.objects.create(name='Perro', slug='perro', icon_name='dog')

        # Mascota activa del usuario principal
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Rocky',
            species=self.species,
            breed='Boxer',
            gender=Pet.Gender.MACHO,
            birth_date='2021-05-10',
            is_active_for_match=True,
        )

        # Mascotas de otros tutores
        self.suitor_pet1 = Pet.objects.create(
            owner=self.other_user,
            name='Kira',
            species=self.species,
            breed='Boxer',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-03-15',
            is_active_for_match=True,
        )

        self.suitor_pet2 = Pet.objects.create(
            owner=self.third_user,
            name='Luna',
            species=self.species,
            breed='Poodle',
            gender=Pet.Gender.HEMBRA,
            birth_date='2023-01-20',
            is_active_for_match=True,
        )

    def test_interested_view_requires_authentication(self):
        """Verifica que la pantalla de interesados requiera autenticación previa."""
        response = self.client.get(reverse('pets:match_interested'))
        self.assertEqual(response.status_code, 302)

    def test_interested_view_renders_successfully_for_authenticated_user(self):
        """Verifica que un usuario autenticado cargue la pantalla con estado 200 y contexto base."""
        self.client.login(username='tutor_interesados', password='password123')
        response = self.client.get(reverse('pets:match_interested'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/match_interested.html')
        self.assertIn('active_pet', response.context)
        self.assertIn('tab_counters', response.context)
        self.assertIn('suitors', response.context)
        self.assertEqual(len(response.context['suitors']), 0)

    def test_tab_counters_calculation(self):
        """
        Verifica el cálculo dinámico de contadores para 'Todos', 'Interesados',
        'Mis solicitudes' y 'Pendientes'.
        """
        # Solicitud entrante 1: Kira -> Rocky (Interesado, pendiente)
        MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
            notes='Interés recibido de Kira',
        )
        # Solicitud saliente: Rocky -> Luna (Enviada)
        MatchRequest.objects.create(
            from_pet=self.pet,
            to_pet=self.suitor_pet2,
            status=MatchRequest.RequestStatus.PENDING,
            notes='Solicitud enviada a Luna',
        )

        counters = get_requests_tab_counters(self.pet)
        self.assertEqual(counters['interested'], 1)
        self.assertEqual(counters['sent'], 1)
        self.assertEqual(counters['pending'], 1)
        self.assertEqual(counters['all'], 2)

    def test_tab_filtering_in_service(self):
        """Verifica que las funciones de servicio devuelvan exactamente las solicitudes correspondientes."""
        req_in = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        req_out = MatchRequest.objects.create(
            from_pet=self.pet,
            to_pet=self.suitor_pet2,
            status=MatchRequest.RequestStatus.PENDING,
        )

        interested_qs = get_interested_match_requests(self.pet)
        sent_qs = get_sent_match_requests(self.pet)
        all_qs = get_all_match_requests_for_pet(self.pet)

        self.assertIn(req_in, interested_qs)
        self.assertNotIn(req_out, interested_qs)

        self.assertIn(req_out, sent_qs)
        self.assertNotIn(req_in, sent_qs)

        self.assertEqual(all_qs.count(), 2)

    def test_interested_view_query_param_tabs(self):
        """Verifica el filtrado por query parameter ?tab=interested y ?tab=sent en la vista."""
        self.client.login(username='tutor_interesados', password='password123')

        MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        MatchRequest.objects.create(
            from_pet=self.pet,
            to_pet=self.suitor_pet2,
            status=MatchRequest.RequestStatus.PENDING,
        )

        # Pestaña interesados (recibidas)
        res_interested = self.client.get(reverse('pets:match_interested') + '?tab=interested')
        self.assertEqual(res_interested.status_code, 200)
        self.assertEqual(len(res_interested.context['suitors']), 1)
        self.assertEqual(res_interested.context['suitors'][0]['name'], 'Kira')

        # Pestaña enviadas
        res_sent = self.client.get(reverse('pets:match_interested') + '?tab=sent')
        self.assertEqual(res_sent.status_code, 200)
        self.assertEqual(len(res_sent.context['suitors']), 1)
        self.assertEqual(res_sent.context['suitors'][0]['name'], 'Luna')

        # Pestaña todos
        res_all = self.client.get(reverse('pets:match_interested') + '?tab=all')
        self.assertEqual(res_all.status_code, 200)
        self.assertEqual(len(res_all.context['suitors']), 2)

    def test_endpoints_require_post(self):
        """Verifica que los endpoints AJAX de transición y nota rechacen métodos GET con 405."""
        self.client.login(username='tutor_interesados', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        res_accept = self.client.get(
            reverse('pets:match_accept_request', kwargs={'request_id': req.id})
        )
        self.assertEqual(res_accept.status_code, 405)

        res_reject = self.client.get(
            reverse('pets:match_reject_request', kwargs={'request_id': req.id})
        )
        self.assertEqual(res_reject.status_code, 405)

        res_msg = self.client.get(
            reverse('pets:send_initial_message', kwargs={'request_id': req.id})
        )
        self.assertEqual(res_msg.status_code, 405)

        res_note = self.client.get(reverse('pets:send_initial_note', kwargs={'request_id': req.id}))
        self.assertEqual(res_note.status_code, 405)

    def test_accept_match_request_transition(self):
        """Verifica que aceptar una solicitud actualice su estado a 'accepted' y sincronice recíproca si existe."""
        self.client.login(username='tutor_interesados', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        # Solicitud inversa previa
        reverse_req = MatchRequest.objects.create(
            from_pet=self.pet,
            to_pet=self.suitor_pet1,
            status=MatchRequest.RequestStatus.PENDING,
        )

        response = self.client.post(
            reverse('pets:match_accept_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['match_status'], 'accepted')
        self.assertEqual(data['request_id'], req.id)

        # Verificar actualización en base de datos
        req.refresh_from_db()
        reverse_req.refresh_from_db()
        self.assertEqual(req.status, MatchRequest.RequestStatus.ACCEPTED)
        self.assertEqual(reverse_req.status, MatchRequest.RequestStatus.ACCEPTED)

    def test_accept_match_request_unauthorized_fails(self):
        """Verifica que un usuario no pueda aceptar solicitudes dirigidas a mascotas que no le pertenecen."""
        # Usuario no dueño intenta aceptar la solicitud dirigida a Rocky
        self.client.login(username='otro_tutor', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet2,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        response = self.client.post(
            reverse('pets:match_accept_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
        req.refresh_from_db()
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)

    def test_reject_match_request_transition(self):
        """Verifica que rechazar o descartar una solicitud actualice su estado a 'rejected'."""
        self.client.login(username='tutor_interesados', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        response = self.client.post(
            reverse('pets:match_reject_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['match_status'], 'rejected')

        req.refresh_from_db()
        self.assertEqual(req.status, MatchRequest.RequestStatus.REJECTED)

    def test_send_initial_message_view(self):
        """Verifica que se registre exitosamente la nota o mensaje inicial de contacto."""
        self.client.login(username='tutor_interesados', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        message_content = (
            '¡Hola Mariana! Encantado con Kira. ¿Coordinamos un paseo en el Parque España?'
        )
        response = self.client.post(
            reverse('pets:send_initial_message', kwargs={'request_id': req.id}),
            data=json.dumps({'message': message_content}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['notes'], message_content)

        req.refresh_from_db()
        self.assertEqual(req.notes, message_content)

    def test_send_initial_message_empty_fails(self):
        """Verifica que enviar un mensaje vacío devuelva error 400."""
        self.client.login(username='tutor_interesados', password='password123')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.post(
            reverse('pets:send_initial_message', kwargs={'request_id': req.id}),
            data=json.dumps({'message': '   '}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    def test_send_initial_message_unauthorized_user_forbidden(self):
        """Verifica que un usuario ajeno a la solicitud no pueda registrar notas en ella."""
        self.client.login(username='tercer_tutor', password='password123')

        # Solicitud entre Kira y Rocky (ninguna pertenece al tercer tutor)
        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.post(
            reverse('pets:send_initial_message', kwargs={'request_id': req.id}),
            data=json.dumps({'message': 'Mensaje no autorizado'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
