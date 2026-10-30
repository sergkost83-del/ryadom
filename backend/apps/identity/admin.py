from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from apps.audit.mixins import AuditedAdminMixin
from apps.communities import roles

from . import twofactor
from .models import User


@admin.register(User)
class UserAdmin(AuditedAdminMixin, admin.ModelAdmin):
    """Только для главного администратора. Пользователей создаёт регистрация, удаляет процедура удаления данных."""

    audit_object_type = "user"
    audit_log_views = True
    list_display = ("email", "display_name", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "display_name")
    list_filter = ("is_active", "is_staff")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "email", "date_joined", "last_login", "deletion_requested_at")
    fields = (
        "id",
        "email",
        "display_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "date_joined",
        "last_login",
        "deletion_requested_at",
    )
    actions = ["make_moderator", "remove_moderator", "reset_two_factor"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def _superuser_only(request):
        if not request.user.is_superuser:
            raise PermissionDenied

    @admin.action(description="Назначить модератором (привязку к ЖК задаёт раздел «Привязки модераторов»)")
    def make_moderator(self, request, queryset):
        self._superuser_only(request)
        for user in queryset:
            roles.promote_to_moderator(user)
            self.audit(request, "make_moderator", user, {"is_staff": [False, True]})

    @admin.action(description="Снять роль модератора (убирает привязки к ЖК и двухфакторную защиту)")
    def remove_moderator(self, request, queryset):
        self._superuser_only(request)
        for user in queryset:
            if roles.demote_moderator(user):
                self.audit(request, "remove_moderator", user, {"is_staff": [True, False]})
            else:
                messages.warning(request, "Главного администратора нельзя лишить роли этим действием.")

    @admin.action(description="Сбросить двухфакторную защиту (при потере телефона и резервных кодов)")
    def reset_two_factor(self, request, queryset):
        self._superuser_only(request)
        for user in queryset:
            twofactor.reset_two_factor(user)
            self.audit(request, "reset_2fa", user)
