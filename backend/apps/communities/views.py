from django.db.models import Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.permissions import ConsentsUpToDate

from .access import notices_visible_to
from .models import Building, Community, Street
from .permissions import IsConfirmedResident


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

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        notices = notices_visible_to(request.user).select_related("building__street")[:50]
        return Response({"notices": [_notice(n) for n in notices]})


class NoticeDetailView(APIView):
    permission_classes = [IsAuthenticated, ConsentsUpToDate, IsConfirmedResident]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk):
        # Чужое объявление выглядит как несуществующее (404), а не «запрещено».
        notice = get_object_or_404(notices_visible_to(request.user).select_related("building__street"), pk=pk)
        return Response(_notice(notice))
