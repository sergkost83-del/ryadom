from django.contrib import admin

from apps.communities.admin_scope import SuperuserOnlyAdminMixin

from .mixins import AuditedAdminMixin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(SuperuserOnlyAdminMixin, AuditedAdminMixin, admin.ModelAdmin):
    """Журнал действий сотрудников. Только чтение, доступен только главному администратору."""

    audit_object_type = "audit_log"
    audit_log_views = True
    list_display = ("created_at", "actor_email", "action", "object_type", "object_id", "community", "ip_address")
    list_filter = ("action", "community")
    search_fields = ("actor_email", "object_id", "action")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
