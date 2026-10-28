from django.conf import settings
from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Session
from .services import ACCESS_SALT


class BearerAuthentication(BaseAuthentication):
    """Authorization: Bearer <access>. Сессия проверяется в базе: выход действует мгновенно."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed("Неверный заголовок Authorization.")
        try:
            data = signing.loads(parts[1], salt=ACCESS_SALT, max_age=settings.AUTH_ACCESS_TTL_SECONDS)
        except signing.BadSignature:
            raise AuthenticationFailed("Токен недействителен или истёк.") from None
        session = Session.objects.select_related("user").filter(pk=data.get("sid"), revoked_at__isnull=True).first()
        if session is None or not session.user.is_active:
            raise AuthenticationFailed("Сессия завершена. Войдите заново.")
        return (session.user, session)

    def authenticate_header(self, request):
        return self.keyword
