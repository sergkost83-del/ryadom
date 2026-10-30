from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.audit.mixins import AuditedAdminMixin

from . import roles, services
from .access import can_moderate_building
from .admin_scope import CommunityScopedAdminMixin, SuperuserOnlyAdminMixin
from .models import (
    AddressChangeRequest,
    Building,
    Community,
    HouseInvite,
    Locality,
    Membership,
    ModeratorAssignment,
    Notice,
    Region,
    Street,
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    search_fields = ("name",)


@admin.register(Community)
class CommunityAdmin(CommunityScopedAdminMixin, admin.ModelAdmin):
    scope_path = "id"
    list_display = ("name", "locality", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Street)
class StreetAdmin(CommunityScopedAdminMixin, admin.ModelAdmin):
    scope_path = "community_id"
    list_display = ("name", "community")
    search_fields = ("name",)


@admin.register(Building)
class BuildingAdmin(CommunityScopedAdminMixin, admin.ModelAdmin):
    scope_path = "street__community_id"
    list_display = ("label", "street", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "street__name")


@admin.register(ModeratorAssignment)
class ModeratorAssignmentAdmin(SuperuserOnlyAdminMixin, AuditedAdminMixin, admin.ModelAdmin):
    """Привязывает модераторов к ЖК. Доступно только главному администратору."""

    audit_object_type = "moderator_assignment"
    list_display = ("user", "community", "created_by", "created_at")
    list_filter = ("community",)
    search_fields = ("user__email",)
    readonly_fields = ("created_by",)
    autocomplete_fields = ()

    def audit_community_id(self, obj):
        return obj.community_id

    def save_model(self, request, obj, form, change):
        if not obj.user.is_active:
            raise PermissionDenied
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        roles.promote_to_moderator(obj.user)  # при первом входе сотрудник настроит двухфакторную защиту


@admin.register(Membership)
class MembershipAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    """Заявки жителей на адрес. Решение принимает модератор этого ЖК или главный администратор."""

    audit_object_type = "membership"
    audit_log_views = True
    scope_path = "building__street__community_id"
    list_display = ("user", "building", "status", "created_at", "confirmed_by")
    list_filter = ("status",)
    search_fields = ("user__email", "building__street__name", "building__label")
    readonly_fields = (
        "user", "building", "role", "status", "confirmed_by", "confirmed_at", "valid_from", "valid_to", "created_at",
    )
    actions = ["confirm_selected", "reject_selected"]

    def audit_community_id(self, obj):
        return obj.building.street.community_id

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _decide(self, request, queryset, new_status, action):
        now = timezone.now()
        for membership in queryset.select_related("building__street").filter(status=Membership.STATUS_PENDING):
            membership.status = new_status
            membership.confirmed_by = request.user
            membership.confirmed_at = now
            membership.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
            self.audit(request, action, membership, {"status": [Membership.STATUS_PENDING, new_status]})

    @admin.action(description="Подтвердить адрес", permissions=["change"])
    def confirm_selected(self, request, queryset):
        self._decide(request, queryset, Membership.STATUS_CONFIRMED, "confirm")

    @admin.action(description="Отклонить заявку", permissions=["change"])
    def reject_selected(self, request, queryset):
        self._decide(request, queryset, Membership.STATUS_REJECTED, "reject")


@admin.register(AddressChangeRequest)
class AddressChangeRequestAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    """Заявки на смену адреса. Решает модератор ЖК, в который переезжает житель, или главный администратор."""

    audit_object_type = "address_change"
    audit_log_views = True
    scope_path = "to_building__street__community_id"
    list_display = ("user", "from_building", "to_building", "status", "created_at", "decided_by")
    list_filter = ("status",)
    search_fields = ("user__email",)
    readonly_fields = (
        "user", "from_building", "to_building", "status", "decided_by", "decided_at", "comment", "via_invite",
        "created_at",
    )
    actions = ["approve_selected", "reject_selected"]

    def audit_community_id(self, obj):
        return obj.to_building.street.community_id

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Одобрить смену адреса", permissions=["change"])
    def approve_selected(self, request, queryset):
        for req in queryset.select_related("to_building__street").filter(status=AddressChangeRequest.STATUS_PENDING):
            if services.approve_address_change(req, request.user):
                changes = {"status": ["pending", "approved"], "to_building": req.to_building_id}
                self.audit(request, "approve", req, changes)

    @admin.action(description="Отклонить заявку", permissions=["change"])
    def reject_selected(self, request, queryset):
        for req in queryset.select_related("to_building__street").filter(status=AddressChangeRequest.STATUS_PENDING):
            if services.reject_address_change(req, request.user):
                self.audit(request, "reject", req, {"status": ["pending", "rejected"]})


@admin.register(Notice)
class NoticeAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    audit_object_type = "notice"
    audit_exclude_fields = ("body",)
    scope_path = "building__street__community_id"
    list_display = ("title", "building", "is_published", "created_at", "created_by")
    list_filter = ("is_published",)
    search_fields = ("title", "building__label", "building__street__name")
    readonly_fields = ("created_by", "created_at")

    def audit_community_id(self, obj):
        return obj.building.street.community_id

    def save_model(self, request, obj, form, change):
        if not can_moderate_building(request.user, obj.building):
            raise PermissionDenied
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class InviteForm(forms.ModelForm):
    expires_in_days = forms.IntegerField(
        label="Срок действия, дней",
        min_value=1,
        max_value=settings.INVITE_MAX_DAYS,
        initial=settings.INVITE_DEFAULT_DAYS,
    )

    class Meta:
        model = HouseInvite
        fields = ("building", "note")


@admin.register(HouseInvite)
class HouseInviteAdmin(AuditedAdminMixin, CommunityScopedAdminMixin, admin.ModelAdmin):
    """Коды приглашения домов: одноразовые, со сроком, с отзывом. Код показывается один раз при создании."""

    audit_object_type = "invite"
    audit_exclude_fields = ("note",)
    scope_path = "building__street__community_id"
    list_display = ("building", "state", "expires_at", "created_by", "used_at", "revoked_at")
    readonly_fields = ("created_by", "expires_at", "used_at", "used_by", "revoked_at", "revoked_by", "created_at")
    actions = ["revoke_selected"]

    def audit_community_id(self, obj):
        return obj.building.street.community_id

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj is None:
            kwargs["form"] = InviteForm
        return super().get_form(request, obj, change=change, **kwargs)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("building", "expires_in_days", "note")
        return ("building", "note", "created_by", "created_at", "expires_at", "used_at", "used_by",
                "revoked_at", "revoked_by")

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ("building", "note", *self.readonly_fields)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Состояние")
    def state(self, obj):
        if obj.used_at:
            return "использован"
        if obj.revoked_at:
            return "отозван"
        return "действует" if obj.is_valid else "истёк"

    def save_model(self, request, obj, form, change):
        if not can_moderate_building(request.user, obj.building):
            raise PermissionDenied
        if change:
            return
        code, code_hash = services.new_invite_secret()
        obj.code_hash = code_hash
        obj.created_by = request.user
        obj.expires_at = timezone.now() + timedelta(days=form.cleaned_data["expires_in_days"])
        super().save_model(request, obj, form, change)
        messages.success(request, f"Код приглашения: {code}. Он показывается один раз, передайте его жителю.")

    @admin.action(description="Отозвать приглашение", permissions=["change"])
    def revoke_selected(self, request, queryset):
        for invite in queryset.select_related("building__street"):
            if services.revoke_invite(invite, request.user):
                self.audit(request, "revoke", invite, {"revoked": ["", "да"]})
