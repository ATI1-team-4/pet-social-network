from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.pets.forms import ScheduleMeetupForm


class ScheduleMeetupFormTests(TestCase):
    """Pruebas unitarias para el formulario de agendamiento de citas entre mascotas."""

    def test_formulario_valido_con_fecha_y_hora_futuras(self):
        """Acepta la propuesta de cita si la fecha y la hora corresponden a un momento futuro."""
        # Calculamos una fecha para mañana en horas de la tarde
        fecha_futura = timezone.localdate() + timedelta(days=1)
        hora_futura = time(16, 30)

        datos = {
            'date': fecha_futura,
            'time': hora_futura,
            'location_name': 'Parque del Este (Área de recreación canina)',
            'notes': 'Traer correa larga y juguetes para socializar.',
        }
        form = ScheduleMeetupForm(data=datos)
        # Comprobamos que el formulario apruebe la validación al tener datos correctos
        self.assertTrue(form.is_valid())

    def test_formulario_rechaza_fecha_en_el_pasado(self):
        """Rechaza la propuesta de cita si la fecha seleccionada ya pasó."""
        # Fecha de ayer
        fecha_pasada = timezone.localdate() - timedelta(days=1)

        datos = {
            'date': fecha_pasada,
            'time': time(10, 0),
            'location_name': 'Parque España (Zona canina verificada)',
            'notes': '',
        }
        form = ScheduleMeetupForm(data=datos)
        # Comprobamos que el formulario rechace la fecha pasada
        self.assertFalse(form.is_valid())
        # Verificamos que el diccionario de errores contenga la clave del campo 'date'
        self.assertIn('date', form.errors)

    def test_formulario_rechaza_hora_pasada_en_el_dia_de_hoy(self):
        """Si la fecha es hoy pero la hora ya transcurrió, el formulario debe ser rechazado."""
        ahora = timezone.localtime()
        fecha_hoy = ahora.date()
        # Calculamos una hora de madrugada anterior a la actual
        hora_pasada = time(0, 1)

        datos = {
            'date': fecha_hoy,
            'time': hora_pasada,
            'location_name': 'Parque Vizcaya',
        }
        form = ScheduleMeetupForm(data=datos)
        # Verificamos solo si la hora actual del día es posterior a medianoche
        if ahora.time() > hora_pasada:
            # Comprobamos que el formulario resulte inválido
            self.assertFalse(form.is_valid())
            # Verificamos que se reporte el error de hora pasada a nivel general o en la fecha
            self.assertTrue('__all__' in form.errors or 'date' in form.errors)

    def test_formulario_rechaza_lugar_vacio_o_en_blanco(self):
        """No permite agendar un encuentro sin indicar el lugar o parque."""
        fecha_futura = timezone.localdate() + timedelta(days=2)

        datos = {
            'date': fecha_futura,
            'time': time(15, 0),
            'location_name': '   ',
            'notes': '',
        }
        form = ScheduleMeetupForm(data=datos)
        # Comprobamos que no sea válido al dejar el lugar en blanco
        self.assertFalse(form.is_valid())
        # Verificamos que el campo 'location_name' contenga el error de validación
        self.assertIn('location_name', form.errors)
