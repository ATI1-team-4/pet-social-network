from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.pets.models import MatchRequest, Pet, PetMeetup, PetSpecies


@admin.register(PetSpecies)
class PetSpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_name', 'is_active', 'created_at')
    search_fields = ('name', 'slug')
    list_filter = ('is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'species',
        'breed',
        'gender',
        'owner',
        'birth_date',
        'purpose',
        'is_active_for_match',
        'profile_color',
    )
    list_filter = (
        'species',
        'gender',
        'purpose',
        'is_active_for_match',
        'profile_color',
        'created_at',
    )
    search_fields = (
        'name',
        'breed',
        'owner__username',
        'owner__email',
        'certificate_number',
    )
    list_editable = ('is_active_for_match',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (
            _('Información básica'),
            {
                'fields': (
                    'owner',
                    'name',
                    'species',
                    'breed',
                    'gender',
                    'birth_date',
                    'weight_kg',
                    'description',
                    'photo',
                )
            },
        ),
        (
            _('Certificados y propósito de match'),
            {
                'fields': (
                    'certificate_type',
                    'certificate_number',
                    'purpose',
                    'is_active_for_match',
                    'max_search_distance_km',
                    'temperaments',
                    'profile_color',
                )
            },
        ),
        (
            _('Metadatos de auditoría'),
            {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )


@admin.register(MatchRequest)
class MatchRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'from_pet',
        'to_pet',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'from_pet__name',
        'to_pet__name',
        'from_pet__owner__username',
        'to_pet__owner__username',
        'notes',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PetMeetup)
class PetMeetupAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'host_pet',
        'guest_pet',
        'date',
        'time',
        'location_name',
        'status',
        'created_at',
    )
    list_filter = ('status', 'date')
    search_fields = (
        'host_pet__name',
        'guest_pet__name',
        'location_name',
        'notes',
    )
    readonly_fields = ('created_at', 'updated_at')
