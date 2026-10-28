from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Building, Community, Street


class CommunityDirectoryView(APIView):
    """Публичный справочник адресов для выбора дома при регистрации. Персональных данных нет."""

    authentication_classes = []
    permission_classes = [AllowAny]

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
