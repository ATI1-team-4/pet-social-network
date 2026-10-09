from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'ip_address')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'action', 'ip_address', 'details')
    readonly_fields = ('created_at', 'updated_at')
