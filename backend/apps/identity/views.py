from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communities.models import Membership

from . import pure, services
from .models import Consent, Session, User
from .serializers import (
    ProfileUpdateSerializer,
    RefreshSerializer,
    RegisterSerializer,
    RequestCodeSerializer,
    VerifyCodeSerializer,
    user_payload,
)


def client_ip(request):
    return pure.extract_client_ip(
        request.META.get("REMOTE_ADDR"),
        request.META.get("HTTP_X_FORWARDED_FOR"),
        settings.TRUSTED_PROXY_COUNT,
    )


class PublicView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class RequestCodeView(PublicView):
    def post(self, request):
        data = RequestCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.request_login_code(data.validated_data["email"], client_ip(request))
        # Ответ одинаков для любого адреса: так нельзя узнать, зарегистрирован ли e-mail.
        return Response({"detail": "Если адрес указан верно, код отправлен."}, status=status.HTTP_202_ACCEPTED)


class VerifyCodeView(PublicView):
    def post(self, request):
        data = VerifyCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        email = services.verify_login_code(
            data.validated_data["email"], data.validated_data["code"], client_ip(request)
        )
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({"is_new": True, "registration_token": services.make_registration_token(email)})
        if not user.is_active:
            raise services.InvalidCode()
        tokens = services.issue_tokens(
            user, data.validated_data["device_name"], request.META.get("HTTP_USER_AGENT", "")
        )
        return Response({"is_new": False, "tokens": tokens, "user": user_payload(user)})


class RegisterView(PublicView):
    def post(self, request):
        data = RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        email = services.read_registration_token(v["registration_token"])
        building = data.context["building"]
        now = timezone.now()
        try:
            with transaction.atomic():
                if User.objects.filter(email=email).exists():
                    raise services.Conflict()
                user = User.objects.create_user(email, display_name=v["display_name"], age_confirmed_at=now)
                Consent.objects.bulk_create(
                    [
                        Consent(user=user, consent_type=kind, version=version, accepted_at=now)
                        for kind, version in v["consents"].items()
                    ]
                )
                Membership.objects.create(user=user, building=building, status=Membership.STATUS_PENDING)
        except IntegrityError:
            raise services.Conflict() from None
        tokens = services.issue_tokens(user, v["device_name"], request.META.get("HTTP_USER_AGENT", ""))
        return Response({"tokens": tokens, "user": user_payload(user)}, status=status.HTTP_201_CREATED)


class RefreshView(PublicView):
    def post(self, request):
        data = RefreshSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response({"tokens": services.rotate_refresh(data.validated_data["refresh"])})


class LogoutView(APIView):
    def post(self, request):
        services.revoke_session(request.auth)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    def post(self, request):
        services.revoke_all_sessions(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(APIView):
    def get(self, request):
        sessions = Session.objects.filter(user=request.user, revoked_at__isnull=True).order_by("-last_seen_at")
        return Response(
            {
                "sessions": [
                    {
                        "id": str(s.id),
                        "device_name": s.device_name,
                        "created_at": s.created_at,
                        "last_seen_at": s.last_seen_at,
                        "current": s.id == request.auth.id,
                    }
                    for s in sessions
                ]
            }
        )


class SessionDetailView(APIView):
    def delete(self, request, pk):
        # Чужая сессия выглядит как несуществующая (404): перебором не узнать, какие бывают.
        session = get_object_or_404(Session, pk=pk, user=request.user)
        services.revoke_session(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(user_payload(request.user))

    def patch(self, request):
        data = ProfileUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        for field, value in data.validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data.validated_data) or None)
        return Response(user_payload(user))


class LegalCurrentView(PublicView):
    def get(self, request):
        return Response({"documents": settings.LEGAL_DOCUMENT_VERSIONS, "minimum_age": settings.MINIMUM_AGE})
