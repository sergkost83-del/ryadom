from rest_framework.permissions import BasePermission

from .services import consents_up_to_date


class ConsentsUpToDate(BasePermission):
    message = "Нужно принять актуальные версии политики и согласия на обработку данных."
    code = "consent_required"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and consents_up_to_date(request.user))
