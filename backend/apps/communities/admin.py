from django.contrib import admin
from django.utils import timezone

from .models import Building, Community, Locality, Membership, Notice, Region, Street


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    search_fields = ("name",)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "locality", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ("name", "community")
    search_fields = ("name",)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("label", "street", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "street__name")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Здесь модератор подтверждает или отклоняет адрес жителя."""

    list_display = ("user", "building", "status", "created_at", "confirmed_by")
    list_filter = ("status",)
    search_fields = ("user__email", "building__street__name", "building__label")
    readonly_fields = ("user", "building", "confirmed_by", "confirmed_at", "created_at")
    actions = ["confirm_selected", "reject_selected"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Подтвердить адрес")
    def confirm_selected(self, request, queryset):
        queryset.filter(status=Membership.STATUS_PENDING).update(
            status=Membership.STATUS_CONFIRMED, confirmed_by=request.user, confirmed_at=timezone.now()
        )

    @admin.action(description="Отклонить заявку")
    def reject_selected(self, request, queryset):
        queryset.filter(status=Membership.STATUS_PENDING).update(
            status=Membership.STATUS_REJECTED, confirmed_by=request.user, confirmed_at=timezone.now()
        )


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "building", "is_published", "created_at", "created_by")
    list_filter = ("is_published",)
    search_fields = ("title", "building__label", "building__street__name")
    readonly_fields = ("created_by", "created_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
