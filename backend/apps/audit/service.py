from django.conf import settings

from apps.identity.pure import extract_client_ip

from .models import AuditLog
from .pure import sanitize_changes


def request_ip(request):
    if request is None:
        return None
    return extract_client_ip(
        request.META.get("REMOTE_ADDR"), request.META.get("HTTP_X_FORWARDED_FOR"), settings.TRUSTED_PROXY_COUNT
    )


def record(*, actor, action, object_type="", object_id="", community_id=None, changes=None, ip=None,
           note="", exclude=()):
    """Добавляет запись в журнал. Секреты из changes вырезаются автоматически."""
    valid_ip = ip if ip and ip != "unknown" else None
    return AuditLog.objects.create(
        actor=actor if actor is not None and getattr(actor, "pk", None) else None,
        actor_email=getattr(actor, "email", "") or "",
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        community_id=community_id,
        changes=sanitize_changes(changes, exclude=exclude),
        ip_address=valid_ip,
        note=(note or "")[:200],
    )
