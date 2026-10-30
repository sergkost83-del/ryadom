from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from . import twofactor


class AdminTwoFactorMiddleware:
    """Сотрудник не попадёт ни на одну страницу админки, пока не подтвердит вход вторым фактором."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prefix = "/" + settings.ADMIN_URL
        path = request.path
        if path.startswith(prefix) and not self._exempt(path, prefix):
            user = request.user
            if user.is_authenticated and user.is_staff and not twofactor.is_verified(request):
                target = "twofactor-verify" if twofactor.confirmed_device(user) else "twofactor-setup"
                return redirect(f"{reverse(target)}?next={quote(path)}")
        return self.get_response(request)

    @staticmethod
    def _exempt(path, prefix):
        return path.startswith((prefix + "login/", prefix + "logout/", prefix + "2fa/", prefix + "jsi18n/"))
