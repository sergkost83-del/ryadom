import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Журнал действий сотрудников с персональными данными. Только добавление; читает только главный администратор.

    Персональных данных жителей (e-mail, телефон) здесь нет: объекты указываются идентификаторами.
    Пароли, коды 2FA и другие секреты в журнал не попадают.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    community = models.ForeignKey(
        "communities.Community", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="audit_log_created"),
            models.Index(fields=["action"], name="audit_log_action"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Записи журнала аудита изменять нельзя.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Записи журнала аудита удалять нельзя.")

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_email} {self.action}"
