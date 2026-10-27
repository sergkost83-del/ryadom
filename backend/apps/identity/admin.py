from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Пользователей создаёт регистрация, а не админка; удаление идёт через процедуру удаления данных."""

    list_display = ("email", "display_name", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "display_name")
    list_filter = ("is_active", "is_staff")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "email", "date_joined", "last_login")
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
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
