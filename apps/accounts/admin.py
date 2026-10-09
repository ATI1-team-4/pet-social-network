from django.contrib import admin

from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'id_type', 'id_number', 'phone_prefix', 'phone_number', 'created_at')
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'id_number',
    )
    list_filter = ('id_type', 'created_at')
