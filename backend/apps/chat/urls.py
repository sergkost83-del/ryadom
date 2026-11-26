from django.urls import path

from . import views

urlpatterns = [
    path("chat/rooms/", views.RoomListView.as_view(), name="chat-rooms"),
    path("chat/rooms/<uuid:pk>/messages/", views.RoomMessagesView.as_view(), name="chat-messages"),
    path("chat/messages/<uuid:pk>/", views.MessageDetailView.as_view(), name="chat-message"),
    path("chat/messages/<uuid:pk>/report/", views.MessageReportView.as_view(), name="chat-message-report"),
    path("chat/messages/<uuid:pk>/block-author/", views.MessageBlockView.as_view(), name="chat-message-block"),
    path("chat/blocks/<uuid:user_id>/", views.UnblockView.as_view(), name="chat-unblock"),
]
