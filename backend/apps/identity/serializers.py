from django.conf import settings
from rest_framework import serializers

from apps.communities.models import Building

from . import pure


class RequestCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Код состоит из 6 цифр."})
    device_name = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")


class RegisterSerializer(serializers.Serializer):
    registration_token = serializers.CharField(max_length=500)
    display_name = serializers.CharField(max_length=100)
    is_adult = serializers.BooleanField()
    consents = serializers.DictField(child=serializers.CharField(max_length=40))
    building_id = serializers.UUIDField()
    device_name = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")

    def validate_display_name(self, value):
        try:
            return pure.clean_display_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None

    def validate_is_adult(self, value):
        if value is not True:
            raise serializers.ValidationError("Регистрация доступна только с 18 лет.")
        return value

    def validate_consents(self, value):
        if value != settings.LEGAL_DOCUMENT_VERSIONS:
            raise serializers.ValidationError(
                "Нужно принять актуальные версии политики и согласия на обработку данных."
            )
        return value

    def validate_building_id(self, value):
        building = (
            Building.objects.select_related("street__community")
            .filter(pk=value, is_active=True, street__community__is_active=True)
            .first()
        )
        if building is None:
            raise serializers.ValidationError("Такого дома нет в справочнике.")
        self.context["building"] = building
        return value


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=200)


class ProfileUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=100, required=False)
    avatar_id = serializers.IntegerField(min_value=1, max_value=8, required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({name: "Это поле нельзя изменить." for name in sorted(unknown)})
        return attrs

    def validate_display_name(self, value):
        try:
            return pure.clean_display_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None

    def validate_phone(self, value):
        try:
            return pure.clean_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None


def membership_payload(user):
    membership = (
        user.memberships.filter(status__in=["pending", "confirmed"])
        .select_related("building__street__community")
        .first()
    )
    if membership is None:
        return None
    building = membership.building
    return {
        "status": membership.status,
        "building": {
            "id": str(building.id),
            "label": building.label,
            "street": building.street.name,
            "community": {"id": str(building.street.community.id), "name": building.street.community.name},
        },
    }


def user_payload(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_id": user.avatar_id,
        "phone": user.phone,
        "account_type": user.account_type,
        "membership": membership_payload(user),
    }
