from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communities.models import Membership

from . import pure, services
from .models import Consent, Session, User
from .serializers import (
    ConsentAcceptSerializer,
    ConsentWithdrawSerializer,
    DeleteAccountSerializer,
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
    @extend_schema(request=RequestCodeSerializer, responses={202: OpenApiTypes.OBJECT})
    def post(self, request):
        data = RequestCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.request_login_code(data.validated_data["email"], client_ip(request))
        # Ответ одинаков для любого адреса: так нельзя узнать, зарегистрирован ли e-mail.
        return Response({"detail": "Если адрес указан верно, код отправлен."}, status=status.HTTP_202_ACCEPTED)


class VerifyCodeView(PublicView):
    @extend_schema(request=VerifyCodeSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        data = VerifyCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        email = services.verify_login_code(
            data.validated_data["email"], data.validated_data["code"], client_ip(request)
        )
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({"is_new": True, "registration_token": services.make_registration_token(email)})
        restored = services.restore_if_within_grace(user)
        if not user.is_active:
            raise services.InvalidCode()
        tokens = services.issue_tokens(
            user, data.validated_data["device_name"], request.META.get("HTTP_USER_AGENT", "")
        )
        return Response({"is_new": False, "restored": restored, "tokens": tokens, "user": user_payload(user)})


class RegisterView(PublicView):
    @extend_schema(request=RegisterSerializer, responses={201: OpenApiTypes.OBJECT})
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
    @extend_schema(request=RefreshSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        data = RefreshSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response({"tokens": services.rotate_refresh(data.validated_data["refresh"])})


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        services.revoke_session(request.auth)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        services.revoke_all_sessions(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
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
    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk):
        # Чужая сессия выглядит как несуществующая (404): перебором не узнать, какие бывают.
        session = get_object_or_404(Session, pk=pk, user=request.user)
        services.revoke_session(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(user_payload(request.user))

    @extend_schema(request=ProfileUpdateSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request):
        data = ProfileUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        for field, value in data.validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data.validated_data) or None)
        return Response(user_payload(user))


class LegalCurrentView(PublicView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({"documents": settings.LEGAL_DOCUMENT_VERSIONS, "minimum_age": settings.MINIMUM_AGE})


def _consent_row(c):
    return {
        "consent_type": c.consent_type,
        "version": c.version,
        "accepted_at": c.accepted_at,
        "withdrawn_at": c.withdrawn_at,
    }


class ConsentListView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        rows = Consent.objects.filter(user=request.user).order_by("accepted_at")
        return Response(
            {
                "required": settings.LEGAL_DOCUMENT_VERSIONS,
                "up_to_date": services.consents_up_to_date(request.user),
                "accepted": [_consent_row(c) for c in rows],
            }
        )


class ConsentAcceptView(APIView):
    @extend_schema(request=ConsentAcceptSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        data = ConsentAcceptSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        now = timezone.now()
        for kind, version in data.validated_data["consents"].items():
            Consent.objects.update_or_create(
                user=request.user,
                consent_type=kind,
                version=version,
                defaults={"accepted_at": now, "withdrawn_at": None},
            )
        return Response({"up_to_date": services.consents_up_to_date(request.user)})


class ConsentWithdrawView(APIView):
    """Отзыв согласия на обработку данных: без него обработка невозможна, поэтому запускается удаление аккаунта."""

    @extend_schema(request=ConsentWithdrawSerializer, responses={202: OpenApiTypes.OBJECT})
    def post(self, request):
        data = ConsentWithdrawSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        kind = data.validated_data["consent_type"]
        if kind != "personal_data":
            raise ValidationError(
                {"consent_type": "Политику нельзя отозвать. Чтобы прекратить обработку данных, отзовите согласие "
                                 "на обработку данных или удалите аккаунт."}
            )
        Consent.objects.filter(user=request.user, consent_type=kind, withdrawn_at__isnull=True).update(
            withdrawn_at=timezone.now()
        )
        erase_at = services.request_account_deletion(request.user)
        return Response({"deletion_scheduled_for": erase_at}, status=status.HTTP_202_ACCEPTED)


class ExportView(APIView):
    """Выгрузка всех данных пользователя (право на доступ к своим данным)."""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        body = {
            "exported_at": timezone.now(),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "avatar_id": user.avatar_id,
                "phone": user.phone,
                "account_type": user.account_type,
                "age_confirmed_at": user.age_confirmed_at,
                "date_joined": user.date_joined,
            },
            "memberships": [
                {
                    "building": str(m.building),
                    "community": m.building.street.community.name,
                    "status": m.status,
                    "role": m.role,
                    "valid_from": m.valid_from,
                    "valid_to": m.valid_to,
                    "confirmed_at": m.confirmed_at,
                }
                for m in user.memberships.select_related("building__street__community")
            ],
            "consents": [_consent_row(c) for c in user.consents.order_by("accepted_at")],
            "sessions": [
                {
                    "id": str(s.id),
                    "device_name": s.device_name,
                    "created_at": s.created_at,
                    "last_seen_at": s.last_seen_at,
                    "revoked_at": s.revoked_at,
                }
                for s in user.sessions.order_by("created_at")
            ],
        }
        response = Response(body)
        response["Content-Disposition"] = 'attachment; filename="ryadom-my-data.json"'
        return response


class DeleteAccountView(APIView):
    @extend_schema(request=DeleteAccountSerializer, responses={202: OpenApiTypes.OBJECT})
    def post(self, request):
        data = DeleteAccountSerializer(data=request.data, context={"user": request.user})
        data.is_valid(raise_exception=True)
        erase_at = services.request_account_deletion(request.user)
        return Response({"deletion_scheduled_for": erase_at}, status=status.HTTP_202_ACCEPTED)
