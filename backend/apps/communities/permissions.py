from rest_framework.permissions import BasePermission

from .access import has_confirmed_membership


class IsConfirmedResident(BasePermission):
    message = "Доступ откроется после подтверждения адреса модератором."
    code = "address_not_confirmed"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and has_confirmed_membership(request.user))
