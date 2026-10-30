from django.core.exceptions import ValidationError

from .service import record, request_ip


class AuditedAdminMixin:
    """Пишет в журнал просмотры, создание, изменение и удаление. Секреты в журнал не попадают."""

    audit_object_type = ""
    audit_log_views = False  # писать просмотры (для моделей с персональными данными)
    audit_exclude_fields = ()  # поля со свободным текстом, которые не копируются в журнал

    def audit_community_id(self, obj):
        return None

    def audit(self, request, action, obj=None, changes=None, note=""):
        record(
            actor=request.user,
            action=f"{self.audit_object_type}.{action}",
            object_type=self.audit_object_type,
            object_id=getattr(obj, "pk", "") or "",
            community_id=self.audit_community_id(obj) if obj is not None else None,
            changes=changes,
            ip=request_ip(request),
            note=note,
            exclude=self.audit_exclude_fields,
        )

    def changelist_view(self, request, extra_context=None):
        if self.audit_log_views and request.method == "GET":
            self.audit(request, "list")
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if self.audit_log_views and request.method == "GET" and object_id:
            try:
                obj = self.get_queryset(request).filter(pk=object_id).first()
            except (ValueError, ValidationError):
                obj = None
            if obj is not None:
                self.audit(request, "view", obj)
            else:
                record(
                    actor=request.user,
                    action=f"{self.audit_object_type}.view_denied",
                    object_type=self.audit_object_type,
                    object_id=str(object_id)[:64],
                    ip=request_ip(request),
                )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            changes = {name: [form.initial.get(name), form.cleaned_data.get(name)] for name in form.changed_data}
            self.audit(request, "update", obj, changes)
        else:
            self.audit(request, "create", obj, {name: form.cleaned_data.get(name) for name in form.changed_data})

    def delete_model(self, request, obj):
        self.audit(request, "delete", obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in list(queryset):
            self.audit(request, "delete", obj)
        super().delete_queryset(request, queryset)
