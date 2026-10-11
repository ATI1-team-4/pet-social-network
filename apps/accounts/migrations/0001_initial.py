import apps.accounts.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avatar', models.ImageField(blank=True, help_text='Fotografía o imagen de perfil del usuario.', null=True, upload_to=apps.accounts.models.user_avatar_upload_path, verbose_name='Avatar')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Momento exacto en el que se creó el registro.', verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Momento de la última modificación del registro.', verbose_name='Última actualización')),
                ('phone_prefix', models.CharField(default='+58', help_text='Prefijo telefónico internacional.', max_length=6, verbose_name='Código de país')),
                ('phone_number', models.CharField(blank=True, help_text='Número de teléfono o contacto del tutor.', max_length=20, verbose_name='Teléfono')),
                ('id_type', models.CharField(default='V', help_text='Nacionalidad o tipo de documento (V, E, J, P).', max_length=2, verbose_name='Tipo de documento')),
                ('id_number', models.CharField(blank=True, help_text='Número de identificación legal del tutor.', max_length=20, verbose_name='Número de cédula/documento')),
                ('bio', models.TextField(blank=True, help_text='Presentación o notas sobre el tutor.', verbose_name='Biografía')),
                ('city', models.CharField(blank=True, default='Caracas', help_text='Ciudad o localidad de residencia del tutor.', max_length=100, verbose_name='Ciudad')),
                ('latitude', models.FloatField(blank=True, help_text='Coordenada geográfica de latitud.', null=True, verbose_name='Latitud')),
                ('longitude', models.FloatField(blank=True, help_text='Coordenada geográfica de longitud.', null=True, verbose_name='Longitud')),
                ('birth_date', models.DateField(blank=True, help_text='Fecha de nacimiento del tutor.', null=True, verbose_name='Fecha de nacimiento')),
                ('gender', models.CharField(blank=True, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], help_text='Género o identidad del tutor.', max_length=1, verbose_name='Género')),
                ('rating', models.DecimalField(decimal_places=2, default=5.0, help_text='Puntuación promedio del tutor (1.00 a 5.00).', max_digits=3, verbose_name='Calificación')),
                ('completed_meetings_count', models.PositiveIntegerField(default=0, help_text='Total de citas de socialización o cruza concretadas.', verbose_name='Citas completadas')),
                ('favorite_color', models.CharField(blank=True, help_text='Color preferido para personalización de perfil.', max_length=50, verbose_name='Color favorito')),
                ('favorite_book', models.CharField(blank=True, help_text='Libro favorito para afinidad cultural.', max_length=200, verbose_name='Libro favorito')),
                ('favorite_music', models.CharField(blank=True, help_text='Género o banda favorita.', max_length=200, verbose_name='Música favorita')),
                ('favorite_videogame', models.CharField(blank=True, help_text='Videojuego preferido.', max_length=200, verbose_name='Videojuego favorito')),
                ('user', models.OneToOneField(help_text='Cuenta de usuario vinculada al perfil.', on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Perfil de usuario',
                'verbose_name_plural': 'Perfiles de usuario',
            },
        ),
        migrations.CreateModel(
            name='UserReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Momento exacto en el que se creó el registro.', verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Momento de la última modificación del registro.', verbose_name='Última actualización')),
                ('reason', models.TextField(help_text='Explicación detallada de la falta o incidente.', verbose_name='Motivo del reporte')),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('reviewed', 'Revisado'), ('action_taken', 'Acción tomada'), ('dismissed', 'Descartado')], default='pending', max_length=20, verbose_name='Estado de revisión')),
                ('admin_notes', models.TextField(blank=True, help_text='Observaciones internas de moderación.', verbose_name='Notas del administrador')),
                ('reported_by', models.ForeignKey(help_text='Usuario tutor que emitió la denuncia.', on_delete=django.db.models.deletion.CASCADE, related_name='reports_filed', to=settings.AUTH_USER_MODEL, verbose_name='Reportado por')),
                ('reported_pet', models.ForeignKey(blank=True, help_text='Mascota específica sobre la que recae el reporte, si aplica.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='pets.pet', verbose_name='Mascota reportada')),
                ('reported_user', models.ForeignKey(help_text='Usuario denunciado.', on_delete=django.db.models.deletion.CASCADE, related_name='reports_received', to=settings.AUTH_USER_MODEL, verbose_name='Usuario reportado')),
            ],
            options={
                'verbose_name': 'Reporte de usuario',
                'verbose_name_plural': 'Reportes de usuarios',
                'ordering': ['-created_at'],
            },
        ),
    ]
