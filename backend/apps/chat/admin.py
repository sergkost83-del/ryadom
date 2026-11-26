from django.contrib import admin, messages
from django.utils import timezone

from apps.audit.mixins import AuditedAdminMixin
from apps.communities.admin_scope import CommunityScopedAdminMixin

from .models import Message, Report, Room


@admin.register(Room)
class RoomAdmin(CommunityScopedAdminMixin, admin.ModelAdmin):
    """Чаты видны только для просмотра; создаются автоматически при появлении подтверждённого адреса."""

    scope_path = "community_id"
    list_display = ("title", "kind", "community")
    list_filter = ("kind",)
    search_fields = ("title",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Message)
class MessageAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    """Модерация сообщений своего ЖК: скрыть сообщение. Текст в журнал аудита не копируется."""

    audit_object_type = "chat_message"
    audit_log_views = True
    audit_exclude_fields = ("body",)
    scope_path = "room__community_id"
    list_display = ("created_at", "room", "author", "deleted_at")
    list_filter = ("room__kind",)
    search_fields = ("body",)
    readonly_fields = ("room", "author", "created_at", "deleted_at", "deleted_by")
    fields = ("room", "author", "body", "created_at", "deleted_at", "deleted_by")
    actions = ["hide_selected"]

    def audit_community_id(self, obj):
        return obj.room.community_id

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("room", "author")

    @admin.action(description="Скрыть выбранные сообщения (нарушение правил)", permissions=["change"])
    def hide_selected(self, request, queryset):
        count = 0
        for message in queryset.select_related("room").filter(deleted_at__isnull=True):
            message.hide(request.user)
            self.audit(request, "hide", message, {"deleted": ["нет", "да"]})
            count += 1
        messages.success(request, f"Скрыто сообщений: {count}.")


@admin.register(Report)
class ReportAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    audit_object_type = "chat_report"
    scope_path = "message__room__community_id"
    list_display = ("created_at", "message", "reporter", "status", "decided_by")
    list_filter = ("status",)
    readonly_fields = ("message", "reporter", "reason", "status", "decided_by", "decided_at", "created_at")
    actions = ["resolve_selected"]

    def audit_community_id(self, obj):
        return obj.message.room.community_id

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Отметить жалобы как рассмотренные", permissions=["change"])
    def resolve_selected(self, request, queryset):
        for report in queryset.select_related("message__room").filter(status="open"):
            report.status = "resolved"
            report.decided_by = request.user
            report.decided_at = timezone.now()
            report.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
            self.audit(request, "resolve", report, {"status": ["open", "resolved"]})
