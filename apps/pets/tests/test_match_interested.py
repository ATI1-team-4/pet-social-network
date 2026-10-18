"""
Pruebas unitarias para la bandeja de interesados y solicitudes de emparejamiento.

Verifica:
- Consulta ORM de solicitudes recibidas y enviadas vinculadas a la mascota activa.
- Cálculo dinámico de contadores para pestañas (todos, interesados, enviadas, pendientes).
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
        # Obtenemos los usuarios correspondientes a desarrolladoras del equipo
        self.user = User.objects.get(username='oriana')
        self.other_user = User.objects.get(username='maria')
        self.third_user = User.objects.get(username='sofia')

        self.species, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )

        # Mascota activa de Oriana
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Rocky',
            species=self.species,
            breed='Boxer',
            gender=Pet.Gender.MACHO,
            birth_date='2021-05-10',
            is_active_for_match=True,
        )

        # Mascotas de María y Sofía
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
        # Comprobamos que el usuario no autenticado sea redirigido con código HTTP 302
        self.assertEqual(response.status_code, 302)

    def test_interested_view_renders_successfully_for_authenticated_user(self):
        """Verifica que un usuario autenticado cargue la pantalla con estado 200 y contexto base."""
        self.client.login(username='oriana', password='123456789')
        response = self.client.get(reverse('pets:match_interested'))
        # Verificamos que la petición responda exitosamente con código 200 (OK)
        self.assertEqual(response.status_code, 200)
        # Comprobamos que Django utilice la plantilla HTML de bandeja de interesados
        self.assertTemplateUsed(response, 'pets/match_interested.html')
        # Verificamos que los elementos esenciales figuren en el contexto de la plantilla
        self.assertIn('active_pet', response.context)
        self.assertIn('tab_counters', response.context)
        self.assertIn('suitors', response.context)
        self.assertEqual(len(response.context['suitors']), 0)

    def test_tab_counters_calculation(self):
        """Verifica el cálculo dinámico de contadores para las diferentes pestañas de solicitudes."""
        # Solicitud entrante: Kira -> Rocky (Interesada, pendiente)
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
        # Comprobamos que cada contador refleje la cantidad exacta según el tipo de solicitud
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

        # Verificamos que la solicitud entrante aparezca solo en la lista de interesados
        self.assertIn(req_in, interested_qs)
        self.assertNotIn(req_out, interested_qs)

        # Verificamos que la solicitud saliente aparezca solo en la lista de enviados
        self.assertIn(req_out, sent_qs)
        self.assertNotIn(req_in, sent_qs)

        # Comprobamos que el total de solicitudes asociadas a la mascota sea 2
        self.assertEqual(all_qs.count(), 2)

    def test_interested_view_query_param_tabs(self):
        """Verifica el filtrado por parámetro GET tab en la vista de interesados."""
        self.client.login(username='oriana', password='123456789')

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

        # Consultamos la pestaña de solicitudes recibidas (interesados)
        res_interested = self.client.get(reverse('pets:match_interested') + '?tab=interested')
        self.assertEqual(res_interested.status_code, 200)
        self.assertEqual(len(res_interested.context['suitors']), 1)
        self.assertEqual(res_interested.context['suitors'][0]['name'], 'Kira')

        # Consultamos la pestaña de solicitudes enviadas
        res_sent = self.client.get(reverse('pets:match_interested') + '?tab=sent')
        self.assertEqual(res_sent.status_code, 200)
        self.assertEqual(len(res_sent.context['suitors']), 1)
        self.assertEqual(res_sent.context['suitors'][0]['name'], 'Luna')

        # Consultamos la pestaña con todas las solicitudes
        res_all = self.client.get(reverse('pets:match_interested') + '?tab=all')
        self.assertEqual(res_all.status_code, 200)
        self.assertEqual(len(res_all.context['suitors']), 2)

    def test_endpoints_require_post(self):
        """Verifica que los endpoints AJAX de transición y notas rechacen métodos GET."""
        self.client.login(username='oriana', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        # Comprobamos que el endpoint de aceptar rechace peticiones GET con código HTTP 405
        res_accept = self.client.get(
            reverse('pets:match_accept_request', kwargs={'request_id': req.id})
        )
        self.assertEqual(res_accept.status_code, 405)

        # Comprobamos que el endpoint de rechazar responda con código HTTP 405
        res_reject = self.client.get(
            reverse('pets:match_reject_request', kwargs={'request_id': req.id})
        )
        self.assertEqual(res_reject.status_code, 405)

        # Comprobamos que el endpoint de nota inicial responda con código HTTP 405
        res_note = self.client.get(reverse('pets:send_initial_note', kwargs={'request_id': req.id}))
        self.assertEqual(res_note.status_code, 405)

    def test_accept_match_request_transition(self):
        """Verifica que aceptar una solicitud actualice su estado a accepted y sincronice la recíproca si existe."""
        self.client.login(username='oriana', password='123456789')

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
        # Verificamos respuesta HTTP exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['match_status'], 'accepted')
        self.assertEqual(data['request_id'], req.id)

        # Recargamos ambas solicitudes desde la base de datos
        req.refresh_from_db()
        reverse_req.refresh_from_db()
        # Comprobamos que ambas solicitudes mutuas hayan pasado a estado ACCEPTED
        self.assertEqual(req.status, MatchRequest.RequestStatus.ACCEPTED)
        self.assertEqual(reverse_req.status, MatchRequest.RequestStatus.ACCEPTED)

    def test_accept_match_request_unauthorized_fails(self):
        """Verifica que un usuario no pueda aceptar solicitudes dirigidas a mascotas que no le pertenecen."""
        # María intenta aceptar una solicitud dirigida a la mascota de Oriana
        self.client.login(username='maria', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet2,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        response = self.client.post(
            reverse('pets:match_accept_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        # Comprobamos que el servidor devuelva código HTTP 404 por no encontrar la solicitud para ese usuario
        self.assertEqual(response.status_code, 404)
        req.refresh_from_db()
        # Verificamos que el estado de la solicitud permanezca intacto en PENDING
        self.assertEqual(req.status, MatchRequest.RequestStatus.PENDING)

    def test_reject_match_request_transition(self):
        """Verifica que rechazar o descartar una solicitud actualice su estado a rejected."""
        self.client.login(username='oriana', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        response = self.client.post(
            reverse('pets:match_reject_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        # Verificamos que responda con código HTTP 200 (éxito)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['match_status'], 'rejected')

        req.refresh_from_db()
        # Comprobamos que el estado en la base de datos sea REJECTED
        self.assertEqual(req.status, MatchRequest.RequestStatus.REJECTED)

    def test_cancel_accepted_match_request(self):
        """Verifica que un tutor pueda cancelar un match previamente aceptado."""
        self.client.login(username='oriana', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.post(
            reverse('pets:match_reject_request', kwargs={'request_id': req.id}),
            content_type='application/json',
        )
        # Verificamos respuesta HTTP exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['match_status'], 'rejected')

        req.refresh_from_db()
        # Comprobamos que el estado en la base de datos cambie a REJECTED
        self.assertEqual(req.status, MatchRequest.RequestStatus.REJECTED)

    def test_send_initial_note_view(self):
        """Verifica que solo el tutor que envía la solicitud pueda redactar la nota inicial."""
        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        note_content = (
            '¡Hola Oriana! Encantada con Rocky. ¿Coordinamos un paseo en el Parque España?'
        )

        # El receptor (Oriana) intenta editar la nota inicial y debe ser denegado con 403
        self.client.login(username='oriana', password='123456789')
        resp_recipient = self.client.post(
            reverse('pets:send_initial_note', kwargs={'request_id': req.id}),
            data=json.dumps({'note': 'Nota del receptor'}),
            content_type='application/json',
        )
        self.assertEqual(resp_recipient.status_code, 403)

        # La remitente que propuso el match (María) redacta la nota inicial
        self.client.login(username='maria', password='123456789')
        response = self.client.post(
            reverse('pets:send_initial_note', kwargs={'request_id': req.id}),
            data=json.dumps({'note': note_content}),
            content_type='application/json',
        )
        # Verificamos respuesta HTTP exitosa con código 200
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['notes'], note_content)

        req.refresh_from_db()
        # Comprobamos que la nota quede registrada en la base de datos
        self.assertEqual(req.notes, note_content)

    def test_send_initial_note_empty_fails(self):
        """Verifica que enviar una nota vacía devuelva error con código HTTP 400."""
        self.client.login(username='maria', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.post(
            reverse('pets:send_initial_note', kwargs={'request_id': req.id}),
            data=json.dumps({'note': '   '}),
            content_type='application/json',
        )
        # Comprobamos que el servidor rechace la nota en blanco con código HTTP 400
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    def test_send_initial_note_unauthorized_user_forbidden(self):
        """Verifica que un usuario ajeno a la solicitud no pueda registrar notas en ella."""
        self.client.login(username='sofia', password='123456789')

        req = MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.ACCEPTED,
        )

        response = self.client.post(
            reverse('pets:send_initial_note', kwargs={'request_id': req.id}),
            data=json.dumps({'note': 'Nota no autorizada'}),
            content_type='application/json',
        )
        # Comprobamos que deniegue el acceso con código HTTP 403 (prohibido)
        self.assertEqual(response.status_code, 403)

    def test_match_interested_sorting_criteria(self):
        """Verifica que el ordenamiento por compatibilidad y por fecha reciente funcione según lo esperado."""
        self.client.login(username='oriana', password='123456789')

        # Solicitud con Kira (misma raza Boxer -> 95% de compatibilidad con Rocky)
        MatchRequest.objects.create(
            from_pet=self.suitor_pet1,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )
        # Solicitud con Luna (Poodle -> 75% de compatibilidad con Rocky, creada posteriormente)
        MatchRequest.objects.create(
            from_pet=self.suitor_pet2,
            to_pet=self.pet,
            status=MatchRequest.RequestStatus.PENDING,
        )

        # Al ordenar por compatibilidad Kira (95%) debe aparecer antes que Luna (75%)
        res_compat = self.client.get(reverse('pets:match_interested') + '?sort=compatibility')
        self.assertEqual(res_compat.status_code, 200)
        suitors = res_compat.context['suitors']
        self.assertEqual(len(suitors), 2)
        self.assertEqual(suitors[0]['name'], 'Kira')
        self.assertEqual(suitors[1]['name'], 'Luna')
        # Comprobamos que los atributos de datos para ordenamiento dinámico estén presentes en el HTML
        self.assertContains(res_compat, 'data-timestamp')
        self.assertContains(res_compat, 'data-compatibility')
        self.assertContains(res_compat, 'data-distance')

        # Al ordenar por fecha reciente Luna (creada de última) debe aparecer primero
        res_recent = self.client.get(reverse('pets:match_interested') + '?sort=recent')
        self.assertEqual(res_recent.status_code, 200)
        suitors_recent = res_recent.context['suitors']
        self.assertEqual(suitors_recent[0]['name'], 'Luna')
        self.assertEqual(suitors_recent[1]['name'], 'Kira')
