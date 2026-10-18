import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

from apps.pets import views
from apps.pets.models import Pet, PetSpecies

User = get_user_model()


class PetsViewsTests(TestCase):
    """Pruebas unitarias para las rutas y vistas de la aplicación pets."""

    def setUp(self):
        # Obtenemos al usuario Edwyn Guzmán y forzamos su sesión activa
        self.user = User.objects.get(username='edwyn')
        self.client.force_login(self.user)

        self.species, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        self.pet_toby = Pet.objects.create(
            owner=self.user,
            name='Toby',
            species=self.species,
            breed='Bulldog Francés',
            gender=Pet.Gender.MACHO,
            birth_date='2022-04-15',
            is_active_for_match=True,
            profile_color='coral',
        )
        self.pet_luna = Pet.objects.create(
            owner=self.user,
            name='Luna',
            species=self.species,
            breed='Golden Retriever',
            gender=Pet.Gender.HEMBRA,
            birth_date='2021-06-20',
            is_active_for_match=True,
            profile_color='lilac',
        )
        # Mascotas de la desarrolladora Sofía Marcano
        sofia = User.objects.get(username='sofia')
        self.cand_bella = Pet.objects.create(
            owner=sofia,
            name='Bella',
            species=self.species,
            breed='Pastor Australiano',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-10-12',
            is_active_for_match=True,
            profile_color='coral',
        )
        self.cand_simba = Pet.objects.create(
            owner=sofia,
            name='Simba',
            species=self.species,
            breed='Golden Retriever',
            gender=Pet.Gender.MACHO,
            birth_date='2022-05-10',
            is_active_for_match=True,
            profile_color='coral',
        )

    def test_unauthenticated_user_redirected_to_login(self):
        """Verifica que un usuario no autenticado sea redirigido a login al intentar acceder a la app."""
        self.client.logout()
        protected_urls = [
            reverse('pets:pet_management'),
            reverse('pets:pet_save'),
            reverse('pets:pet_delete', kwargs={'pet_id': '1234'}),
            reverse('pets:pet_select'),
            reverse('pets:pet_set_active'),
            reverse('pets:match_feed'),
            reverse('pets:match_interested'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            # Comprobamos que el usuario anónimo sea redirigido al formulario de inicio de sesión
            self.assertRedirects(response, f'{reverse("accounts:login")}?next={url}')

    def test_pet_management_url_and_view(self):
        """El formulario de gestión de mascotas carga correctamente para usuarios autenticados."""
        url = reverse('pets:pet_management')
        # Verificamos que la URL resuelva hacia la función de vista pet_management_view
        self.assertEqual(resolve(url).func, views.pet_management_view)
        response = self.client.get(url)
        # Comprobamos que el servidor devuelva código HTTP 200 (éxito)
        self.assertEqual(response.status_code, 200)
        # Verificamos que Django utilice la plantilla HTML de gestión de mascotas
        self.assertTemplateUsed(response, 'pets/pet_management.html')

    def test_pet_select_url_and_view(self):
        """El selector de mascotas lista las mascotas del usuario autenticado y refleja la mascota activa."""
        url = reverse('pets:pet_select')
        # Verificamos que la URL apunte a la función pet_select_view
        self.assertEqual(resolve(url).func, views.pet_select_view)

        # Cargar el listado inicial con las mascotas de Edwyn
        response = self.client.get(url)
        # Comprobamos respuesta HTTP exitosa con código 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que se renderice la plantilla HTML de selección de mascota
        self.assertTemplateUsed(response, 'pets/pet_select.html')
        # Comprobamos que el contexto incluya el listado de mascotas y la mascota activa
        self.assertIn('pets', response.context)
        self.assertIn('active_pet', response.context)
        # Verificamos que los nombres de las mascotas aparezcan en el HTML
        self.assertContains(response, 'Toby')
        self.assertContains(response, 'Luna')

        # Comprobar la selección activa almacenada en la sesión
        session = self.client.session
        session['active_pet_id'] = str(self.pet_luna.id)
        session.save()
        response_luna = self.client.get(url)
        self.assertEqual(response_luna.status_code, 200)
        self.assertEqual(response_luna.context['active_pet']['name'], 'Luna')

        # Verificar que una mascota sin pedigrí no muestre pedigrí certificado
        pet_sin = Pet.objects.create(
            owner=self.user,
            name='Maya',
            species=self.species,
            breed='Boston Terrier',
            gender=Pet.Gender.HEMBRA,
            birth_date='2022-01-08',
            is_active_for_match=True,
            certificate_type='Sin pedigrí',
            certificate_number='',
            profile_color='mint',
        )
        self.assertFalse(pet_sin.has_pedigree)
        self.assertEqual(pet_sin.certificate, 'sin_pedigri')
        response_user = self.client.get(url)
        maya_in_ctx = next((p for p in response_user.context['pets'] if p['name'] == 'Maya'), None)
        self.assertIsNotNone(maya_in_ctx)
        self.assertFalse(maya_in_ctx['has_pedigree'])
        self.assertNotEqual(maya_in_ctx['certificate'], 'fci')

        # Confirmar que otro usuario sólo pueda ver sus propias mascotas
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_sofia = self.client.get(url)
        self.assertEqual(response_sofia.status_code, 200)
        # Comprobamos que aparezcan las mascotas de Sofía
        self.assertContains(response_sofia, 'Bella')
        self.assertContains(response_sofia, 'Simba')
        # Verificamos que las mascotas de Edwyn no aparezcan en la vista de Sofía
        self.assertNotContains(response_sofia, 'Toby')

    def test_match_feed_url_and_view(self):
        """La vista de búsqueda de pareja carga la plantilla correspondiente para el usuario."""
        url = reverse('pets:match_feed')
        self.assertEqual(resolve(url).func, views.match_feed_view)
        response = self.client.get(url)
        # Comprobamos respuesta HTTP 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que se renderice la plantilla HTML del feed de match
        self.assertTemplateUsed(response, 'pets/match_feed.html')

    def test_match_interested_url_and_view(self):
        """La vista de solicitudes de interés carga su plantilla con código HTTP 200."""
        url = reverse('pets:match_interested')
        self.assertEqual(resolve(url).func, views.match_interested_view)
        response = self.client.get(url)
        # Comprobamos respuesta HTTP 200
        self.assertEqual(response.status_code, 200)
        # Verificamos que se renderice la plantilla HTML de bandeja de interesados
        self.assertTemplateUsed(response, 'pets/match_interested.html')

    def test_pet_management_query_params(self):
        """Verifica la carga de mascotas por sesión."""
        session = self.client.session
        session['active_pet_id'] = str(self.pet_luna.id)
        session.save()
        url = reverse('pets:pet_management')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_pet']['name'], 'Luna')
        self.assertContains(response, 'Luna')

        # Solicitud de creación de nueva mascota con el parámetro new=true
        url_new = reverse('pets:pet_management') + '?new=true'
        response_new = self.client.get(url_new)
        self.assertEqual(response_new.status_code, 200)
        self.assertContains(response_new, 'Registrar mascota')

    def test_pet_save_view(self):
        """Verifica el guardado y actualización de mascotas mediante la vista dedicada pet_save_view."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.pets.models import Pet

        save_url = reverse('pets:pet_save')
        response_save = self.client.post(
            save_url, {'name': 'Toby', 'pet_id': str(self.pet_toby.id)}
        )
        # Comprobamos que tras guardar redirija a la pantalla de gestión de mascotas
        self.assertRedirects(response_save, reverse('pets:pet_management'))

        # Verificamos que rechace solicitudes GET con código HTTP 405 (método no permitido)
        response_get = self.client.get(save_url)
        self.assertEqual(response_get.status_code, 405)

        # Guardado con archivo de fotografía adjunto
        photo_file = SimpleUploadedFile(
            'dog.jpg', b'\x47\x49\x46\x38\x39\x61', content_type='image/jpeg'
        )
        response_photo = self.client.post(
            save_url,
            {
                'name': 'Maximus',
                'breed': 'Husky',
                'species': 'perro',
                'gender': 'M',
                'birth_date': '2023-01-01',
                'photo': photo_file,
            },
        )

        saved_pet = Pet.objects.filter(owner=self.user, name='Maximus').first()
        self.assertIsNotNone(saved_pet)
        self.assertRedirects(response_photo, reverse('pets:pet_management'))
        # Comprobamos que la mascota tenga foto y que la ruta comience con el prefijo esperado
        self.assertTrue(saved_pet.has_photo)
        self.assertTrue(
            saved_pet.photo.name.startswith(f'pets/user_{self.user.id}_pet_{saved_pet.id}_avatar_')
        )

    def test_pet_delete_view(self):
        """Verifica la eliminación de mascotas mediante la vista dedicada pet_delete_view."""
        from datetime import date

        from apps.pets.models import Pet, PetSpecies

        species_dog, _ = PetSpecies.objects.get_or_create(
            slug='perro',
            defaults={'name': 'Perro', 'icon_name': 'dog'},
        )
        pet = Pet.objects.create(
            owner=self.user,
            name='Max',
            species=species_dog,
            breed='Labrador',
            birth_date=date(2023, 1, 1),
            purpose=Pet.Purpose.BOTH,
        )
        url = reverse('pets:pet_delete', kwargs={'pet_id': str(pet.id)})

        # Comprobamos que rechace peticiones GET con código 405
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Enviamos la petición POST para eliminar la mascota
        response_post = self.client.post(url)
        self.assertRedirects(response_post, reverse('pets:pet_management'))
        # Verificamos que la mascota ya no exista en la base de datos
        self.assertFalse(Pet.objects.filter(id=pet.id).exists())

    def test_pet_toggle_goal_view(self):
        """Verifica la actualización asíncrona de objetivos en PetMatch (matching, socializing, adoption)."""
        url = reverse('pets:pet_toggle_goal')

        # Comprobamos que rechace peticiones GET con código 405
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Desactivar la opción de buscar pareja
        response_matching = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_matching', 'value': False}),
            content_type='application/json',
        )
        self.assertEqual(response_matching.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertFalse(self.pet_toby.is_matching)
        self.assertFalse(self.pet_toby.is_active_for_match)

        # Activar la opción de mascota en adopción
        response_adoption = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_adoption', 'value': True}),
            content_type='application/json',
        )
        self.assertEqual(response_adoption.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertTrue(self.pet_toby.is_adoption)
        self.assertTrue(self.pet_toby.is_for_adoption)

        # Desactivar la opción de socialización
        response_social = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_socializing', 'value': False}),
            content_type='application/json',
        )
        self.assertEqual(response_social.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertFalse(self.pet_toby.is_socializing)

        # Intentar modificar una mascota ajena con la cuenta de Sofía
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_forbidden = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'goal': 'is_matching', 'value': True}),
            content_type='application/json',
        )
        # Comprobamos que el servidor retorne código HTTP 404 al no encontrar la mascota para ese usuario
        self.assertEqual(response_forbidden.status_code, 404)

    def test_pet_update_certificate_view(self):
        """Verifica la actualización asíncrona del tipo de pedigrí y certificado."""
        url = reverse('pets:pet_update_certificate')

        # Rechazar solicitudes GET
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # Cambiar el tipo a trámite
        response_tramite = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'tramite'}),
            content_type='application/json',
        )
        self.assertEqual(response_tramite.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'tramite')
        self.assertEqual(self.pet_toby.certificate_type, 'En trámite')

        # Cambiar el tipo a sin pedigrí
        response_sin = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'sin_pedigri'}),
            content_type='application/json',
        )
        self.assertEqual(response_sin.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'sin_pedigri')
        self.assertEqual(self.pet_toby.certificate_type, 'Sin pedigrí')

        # Cambiar el tipo a certificado FCI
        response_fci = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'fci'}),
            content_type='application/json',
        )
        self.assertEqual(response_fci.status_code, 200)
        self.pet_toby.refresh_from_db()
        self.assertEqual(self.pet_toby.certificate, 'fci')
        self.assertEqual(self.pet_toby.certificate_type, 'Certificado FCI')

        # Mascota ajena no accesible para Sofía
        sofia = User.objects.get(username='sofia')
        self.client.force_login(sofia)
        response_forbidden = self.client.post(
            url,
            json.dumps({'pet_id': self.pet_toby.id, 'certificate': 'tramite'}),
            content_type='application/json',
        )
        self.assertEqual(response_forbidden.status_code, 404)

    def test_pet_set_active_view(self):
        """Verifica que la vista dedicada pet_set_active_view guarde en sesión y redirija al feed."""
        url = reverse('pets:pet_set_active')

        # Rechazar solicitudes GET
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        response = self.client.post(
            url,
            {
                'selected_pet_id': str(self.pet_luna.id),
                'pedigree_filter': 'without_pedigree',
            },
        )
        # Comprobamos que redirija al feed de parejas
        self.assertRedirects(response, reverse('pets:match_feed'))
        # Verificamos que los datos hayan quedado almacenados en la sesión del cliente
        self.assertEqual(self.client.session.get('active_pet_id'), str(self.pet_luna.id))
        self.assertEqual(self.client.session.get('match_pedigree_preference'), 'without_pedigree')

        # Probar redirección con next_url personalizado
        response_next = self.client.post(
            url,
            {
                'selected_pet_id': str(self.pet_toby.id),
                'next_url': reverse('pets:pet_management'),
            },
        )
        self.assertRedirects(response_next, reverse('pets:pet_management'))
        self.assertEqual(self.client.session.get('active_pet_id'), str(self.pet_toby.id))

    def test_match_feed_view_context_and_content(self):
        """Verifica que el feed de cruza cargue candidatos, color de perfil y enlaces."""
        url = reverse('pets:match_feed')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Verificamos que el contexto de la plantilla contenga las variables requeridas
        self.assertIn('active_pet', response.context)
        self.assertIn('candidates', response.context)
        self.assertIn('candidates_json', response.context)
        self.assertIn('interested_sidebar', response.context)

        # Comprobamos que el nombre de la candidata y los enlaces aparezcan en el HTML
        self.assertContains(response, 'Bella')
        self.assertContains(response, 'Pastor Australiano')
        self.assertContains(response, reverse('pets:pet_select'))
        self.assertContains(response, reverse('pets:match_interested'))

        # Verificamos que al seleccionar a Luna en sesión se aplique su color de perfil
        session = self.client.session
        session['active_pet_id'] = str(self.pet_luna.id)
        session.save()
        response_luna = self.client.get(reverse('pets:match_feed'))
        self.assertEqual(response_luna.status_code, 200)
        self.assertEqual(response_luna.context['active_pet']['name'], 'Luna')
        self.assertContains(response_luna, response_luna.context['active_pet']['profile_color_hex'])

    def test_match_interested_view_context_and_content(self):
        """Verifica que la bandeja de interesados cargue pretendientes, citas y enlaces."""
        from apps.pets.models import MatchRequest, Pet

        sofia = User.objects.get(username='sofia')
        cand_kira = Pet.objects.create(
            owner=sofia,
            name='Kira',
            species=self.species,
            breed='Pomerania Mini',
            gender=Pet.Gender.HEMBRA,
            birth_date='2023-06-15',
            is_active_for_match=True,
        )
        MatchRequest.objects.create(
            from_pet=cand_kira,
            to_pet=self.pet_toby,
            status=MatchRequest.RequestStatus.PENDING,
            notes='¡Hola! Nos encantó Toby.',
        )

        url = reverse('pets:match_interested')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Verificamos variables de contexto
        self.assertIn('featured_suitor', response.context)
        self.assertIn('secondary_suitors', response.context)
        self.assertIn('confirmed_dates', response.context)

        # Comprobamos que el nombre y raza del pretendiente figuren en la respuesta
        self.assertContains(response, 'Kira')
        self.assertContains(response, 'Pomerania Mini')

        # Verificamos la sección de citas y el enlace de retorno al feed
        self.assertContains(response, 'Citas y encuentros')
        self.assertContains(response, reverse('pets:match_feed'))

    def test_user_without_pets_onboarding_and_defaults(self):
        """Verifica que un usuario nuevo sin mascotas sea guiado a crear una y las vistas no fallen."""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        new_user = user_model.objects.create_user(
            username='usuario_nuevo',
            email='nuevo@petly.com',
            password='Password123!',
        )
        self.client.force_login(new_user)

        # En la pantalla de gestión debe marcar is_new=True y no tener mascotas registradas
        res_mgmt = self.client.get(reverse('pets:pet_management'))
        self.assertEqual(res_mgmt.status_code, 200)
        self.assertTrue(res_mgmt.context['is_new'])
        self.assertEqual(len(res_mgmt.context['pets']), 0)
        self.assertContains(res_mgmt, '¡Te damos la bienvenida a Petly!')

        # Al entrar al selector de mascotas debe redirigir al formulario de registro
        res_sel = self.client.get(reverse('pets:pet_select'))
        self.assertRedirects(res_sel, f'{reverse("pets:pet_management")}?new=true')

        # Al entrar al feed de match debe redirigir al formulario de registro
        res_feed = self.client.get(reverse('pets:match_feed'))
        self.assertRedirects(res_feed, f'{reverse("pets:pet_management")}?new=true')

        # Al entrar a la bandeja de interesados debe redirigir al formulario de registro
        res_int = self.client.get(reverse('pets:match_interested'))
        self.assertRedirects(res_int, f'{reverse("pets:pet_management")}?new=true')
