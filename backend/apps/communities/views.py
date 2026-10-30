from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.service import record, request_ip
from apps.identity import services as identity_services
from apps.identity.permissions import ConsentsUpToDate
from apps.identity.serializers import membership_payload

from . import services
from .access import notices_visible_to
from .models import AddressChangeRequest, Building, Community, Street
from .permissions import IsConfirmedResident
from .serializers import AddressChangeSerializer


class CommunityDirectoryView(APIView):
    """Публичный справочник адресов для выбора дома при регистрации. Персональных данных нет."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        buildings = Prefetch("buildings", queryset=Building.objects.filter(is_active=True))
        streets = Prefetch("streets", queryset=Street.objects.prefetch_related(buildings))
        communities = (
            Community.objects.filter(is_active=True).select_related("locality__region").prefetch_related(streets)
        )
        return Response(
            {
                "communities": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "slug": c.slug,
                        "locality": c.locality.name,
                        "streets": [
                            {
                                "id": str(s.id),
                                "name": s.name,
                                "buildings": [{"id": str(b.id), "label": b.label} for b in s.buildings.all()],
                            }
                            for s in c.streets.all()
                        ],
                    }
                    for c in communities
                ]
            }
        )


def _notice(n):
    return {
        "id": str(n.id),
        "title": n.title,
        "body": n.body,
        "created_at": n.created_at,
        "building": {"id": str(n.building_id), "label": n.building.label, "street": n.building.street.name},
    }


class NoticeListView(APIView):
    """Объявления домов, где пользователь — подтверждённый житель. Чужие дома не видны."""

    permission_classes = [IsAuthenticated, ConsentsUpToDate, IsConfirmedResident]

    @extend_schema(operation_id="notices_list", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        notices = notices_visible_to(request.user).select_related("building__street")[:50]
        return Response({"notices": [_notice(n) for n in notices]})


class NoticeDetailView(APIView):
    permission_classes = [IsAuthenticated, ConsentsUpToDate, IsConfirmedResident]

    @extend_schema(operation_id="notices_detail", responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk):
        # Чужое объявление выглядит как несуществующее (404), а не «запрещено».
        notice = get_object_or_404(notices_visible_to(request.user).select_related("building__street"), pk=pk)
        return Response(_notice(notice))


def _request_payload(req):
    building = req.to_building
    return {
        "id": str(req.id),
        "status": req.status,
        "to_building": {
            "id": str(building.id),
            "label": building.label,
            "street": building.street.name,
            "community": {"id": str(building.street.community_id), "name": building.street.community.name},
        },
        "created_at": req.created_at,
        "decided_at": req.decided_at,
        "comment": req.comment,
    }


def _latest_request(user):
    queryset = AddressChangeRequest.objects.filter(user=user).select_related("to_building__street__community")
    pending = queryset.filter(status=AddressChangeRequest.STATUS_PENDING).first()
    return pending or queryset.order_by("-created_at").first()


class AddressChangeView(APIView):
    """Заявка на смену адреса. Решает модератор ЖК, куда переезжает житель, либо код приглашения этого дома."""

    permission_classes = [IsAuthenticated, ConsentsUpToDate]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        req = _latest_request(request.user)
        return Response(
            {"membership": membership_payload(request.user), "request": _request_payload(req) if req else None}
        )

    @extend_schema(request=AddressChangeSerializer, responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT})
    def post(self, request):
        if request.data.get("invite_code"):
            ip = request_ip(request)
            identity_services.check_throttle("invite-ip", ip, settings.INVITE_ATTEMPTS_PER_IP_HOUR, 3600)
        data = AddressChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        building, invite = data.context["building"], data.context["invite"]
        user = request.user
        current = services.current_building(user)
        if current is not None and current.pk == building.pk:
            raise ValidationError({"building_id": "Этот адрес уже закреплён за вами."})
        now = timezone.now()
        try:
            with transaction.atomic():
                pending = AddressChangeRequest.objects.select_for_update().filter(
                    user=user, status=AddressChangeRequest.STATUS_PENDING
                ).first()
                if invite:
                    services.consume_invite(invite, user)
                    if pending:
                        pending.status = AddressChangeRequest.STATUS_CANCELLED
                        pending.save(update_fields=["status", "updated_at"])
                    services.apply_membership(user, building, invite.created_by)
                    req = AddressChangeRequest.objects.create(
                        user=user, from_building=current, to_building=building,
                        status=AddressChangeRequest.STATUS_APPROVED, decided_by=invite.created_by,
                        decided_at=now, via_invite=invite,
                    )
                else:
                    if pending:
                        raise identity_services.Conflict(
                            "У вас уже есть заявка на смену адреса. Отмените её или дождитесь решения."
                        )
                    req = AddressChangeRequest.objects.create(user=user, from_building=current, to_building=building)
        except IntegrityError:
            raise identity_services.Conflict("У вас уже есть заявка на смену адреса.") from None
        if invite:
            record(actor=None, action="address_change.approved_by_invite", object_type="address_change",
                   object_id=req.pk, community_id=building.street.community_id, ip=request_ip(request),
                   changes={"to_building": building.pk}, note="смена адреса по коду приглашения")
        req = AddressChangeRequest.objects.select_related("to_building__street__community").get(pk=req.pk)
        code = status.HTTP_200_OK if invite else status.HTTP_201_CREATED
        return Response({"request": _request_payload(req)}, status=code)


class AddressChangeCancelView(APIView):
    permission_classes = [IsAuthenticated, ConsentsUpToDate]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        updated = AddressChangeRequest.objects.filter(
            user=request.user, status=AddressChangeRequest.STATUS_PENDING
        ).update(status=AddressChangeRequest.STATUS_CANCELLED, updated_at=timezone.now())
        if not updated:
            raise NotFound("Активной заявки нет.")
        return Response(status=status.HTTP_204_NO_CONTENT)
