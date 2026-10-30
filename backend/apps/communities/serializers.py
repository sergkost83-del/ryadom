from rest_framework import serializers

from .models import Building
from .services import find_valid_invite

INVALID_INVITE = "Код приглашения недействителен или истёк."


class AddressChangeSerializer(serializers.Serializer):
    building_id = serializers.UUIDField(required=False)
    invite_code = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate(self, attrs):
        code = attrs.get("invite_code")
        invite = None
        if code:
            invite = find_valid_invite(code)
            if invite is None or (attrs.get("building_id") and attrs["building_id"] != invite.building_id):
                raise serializers.ValidationError({"invite_code": INVALID_INVITE})
            building = invite.building
        elif attrs.get("building_id"):
            building = (
                Building.objects.select_related("street__community")
                .filter(pk=attrs["building_id"], is_active=True, street__community__is_active=True)
                .first()
            )
            if building is None:
                raise serializers.ValidationError({"building_id": "Такого дома нет в справочнике."})
        else:
            raise serializers.ValidationError({"building_id": "Укажите дом или код приглашения."})
        self.context["building"] = building
        self.context["invite"] = invite
        return attrs
