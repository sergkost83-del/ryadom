from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.permissions import ConsentsUpToDate

from . import services
from .access import visible_rooms
from .models import Message
from .serializers import BodySerializer, ReportSerializer, message_payload, room_payload


class ChatBase(APIView):
    permission_classes = [IsAuthenticated, ConsentsUpToDate]


class RoomListView(ChatBase):
    @extend_schema(operation_id="chat_rooms_list", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        services.ensure_rooms(request.user)
        return Response({"rooms": [room_payload(r) for r in visible_rooms(request.user)]})


class RoomMessagesView(ChatBase):
    @extend_schema(operation_id="chat_messages_list", responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk):
        room = services.get_room_for(request.user, pk)
        before = None
        if request.query_params.get("before"):
            before = parse_datetime(request.query_params["before"])
            if before is None:
                raise ValidationError({"before": "Укажите дату и время в формате ISO 8601."})
        limit = request.query_params.get("limit", 30)
        messages = services.list_messages(request.user, room, before=before, limit=limit)
        return Response({"messages": [message_payload(m, request.user) for m in messages]})

    @extend_schema(operation_id="chat_messages_create", request=BodySerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request, pk):
        room = services.get_room_for(request.user, pk)
        data = BodySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        message = services.post_message(request.user, room, data.validated_data["body"])
        return Response(message_payload(message, request.user), status=status.HTTP_201_CREATED)


def _message_for(request, pk) -> Message:
    message = Message.objects.select_related("room", "author").filter(pk=pk, deleted_at__isnull=True).first()
    if message is None:
        raise NotFound()
    services.get_room_for(request.user, message.room_id)  # проверка доступа к чату
    return message


class MessageDetailView(ChatBase):
    @extend_schema(operation_id="chat_message_delete", responses={204: None})
    def delete(self, request, pk):
        message = _message_for(request, pk)
        services.delete_own_message(request.user, message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageReportView(ChatBase):
    @extend_schema(
        operation_id="chat_message_report",
        request=ReportSerializer,
        responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        message = _message_for(request, pk)
        data = ReportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        report, created = services.report_message(request.user, message, data.validated_data["reason"])
        return Response({"id": str(report.id), "status": report.status}, status=201 if created else 200)


class MessageBlockView(ChatBase):
    @extend_schema(operation_id="chat_message_block_author", request=None, responses={201: OpenApiTypes.OBJECT})
    def post(self, request, pk):
        message = _message_for(request, pk)
        block = services.block_author(request.user, message)
        return Response({"blocked_user_id": str(block.blocked_id)}, status=status.HTTP_201_CREATED)


class UnblockView(ChatBase):
    @extend_schema(operation_id="chat_unblock", responses={204: None})
    def delete(self, request, user_id):
        services.unblock(request.user, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
