from django.core.exceptions import PermissionDenied

from .access import moderated_community_ids
from .models import Building


class CommunityScopedAdminMixin:
    """Ограничивает админку ЖК модератора на уровне запросов и прав на объект, а не только скрытием пунктов меню.

    scope_path — путь от модели до идентификатора ЖК, например «building__street__community_id».
    Главный администратор видит всё; модератор без привязок не видит ничего.
    """

    scope_path = None
    building_fields = ("building", "to_building")

    def scope_ids(self, request):
        return moderated_community_ids(request.user)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        ids = self.scope_ids(request)
        if ids is None:
            return queryset
        return queryset.filter(**{f"{self.scope_path}__in": ids})

    def _in_scope(self, request, obj):
        if obj is None:
            return True
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._in_scope(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._in_scope(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._in_scope(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        ids = self.scope_ids(request)
        if ids is not None and db_field.name in self.building_fields:
            kwargs["queryset"] = Building.objects.filter(street__community_id__in=ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def require_scope(self, request, obj):
        """Повторная проверка перед записью (на случай обхода формы)."""
        if not self._in_scope(request, obj) and obj.pk is not None:
            raise PermissionDenied


class SuperuserOnlyAdminMixin:
    """Раздел доступен только главному администратору."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser
