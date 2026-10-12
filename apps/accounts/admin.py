from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import UserProfile, UserReport
from apps.pets.models import Pet

User = get_user_model()


class PetInline(admin.TabularInline):
    model = Pet
    extra = 0
    fields = ('name', 'species', 'breed', 'gender', 'purpose', 'is_active_for_match')
    readonly_fields = ()
    show_change_link = True
    verbose_name = _('Mascota')
    verbose_name_plural = _('Mascotas registradas')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = _('Perfil adicional')
    verbose_name_plural = _('Perfil adicional')
    fields = (
        ('id_type', 'id_number'),
        ('phone_prefix', 'phone_number'),
        ('state', 'municipality', 'neighborhood'),
        ('latitude', 'longitude'),
        ('birth_date', 'gender'),
        ('get_rating_display', 'get_meetings_display'),
        ('favorite_color', 'favorite_book'),
        ('favorite_music', 'favorite_videogame'),
        'bio',
    )
    readonly_fields = ('get_rating_display', 'get_meetings_display')

    @admin.display(description=_('Calificación'))
    def get_rating_display(self, obj):
        return obj.rating if obj else '-'

    @admin.display(description=_('Citas completadas'))
    def get_meetings_display(self, obj):
        return obj.completed_meetings_count if obj else 0


# Re-registrar UserAdmin para incluir perfil y mascotas
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline, PetInline]
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'get_city',
        'get_rating',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    @admin.display(description=_('Ciudad / Ubicación'))
    def get_city(self, obj):
        return obj.profile.city if hasattr(obj, 'profile') else '-'

    @admin.display(description=_('Calificación'))
    def get_rating(self, obj):
        return obj.profile.rating if hasattr(obj, 'profile') else '-'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'state',
        'municipality',
        'neighborhood',
        'get_rating',
        'get_completed_meetings',
        'id_type',
        'id_number',
        'phone_prefix',
        'phone_number',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'id_number',
        'state',
        'municipality',
        'neighborhood',
    )
    list_filter = ('id_type', 'state', 'municipality', 'created_at')

    @admin.display(description=_('Calificación'))
    def get_rating(self, obj):
        return obj.rating

    @admin.display(description=_('Citas completadas'))
    def get_completed_meetings(self, obj):
        return obj.completed_meetings_count


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reported_by',
        'reported_user',
        'reported_pet',
        'status',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'reported_by__username',
        'reported_user__username',
        'reported_pet__name',
        'reason',
        'admin_notes',
    )
    actions = ['ban_reported_user']

    @admin.action(description=_('Suspender usuario reportado (bloqueo) y marcar acción tomada'))
    def ban_reported_user(self, request, queryset):
        count = 0
        for report in queryset:
            user = report.reported_user
            if user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
            report.status = UserReport.ReportStatus.ACTION_TAKEN
            if not report.admin_notes:
                report.admin_notes = _(
                    'Usuario suspendido automáticamente mediante acción del panel de moderación.'
                )
            report.save(update_fields=['status', 'admin_notes'])
            count += 1

        self.message_user(
            request,
            _('%(count)d reportes procesados: usuarios suspendidos exitosamente.')
            % {'count': count},
            messages.SUCCESS,
        )
