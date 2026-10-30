from django.urls import path

from .views import (
    AddressChangeCancelView,
    AddressChangeView,
    CommunityDirectoryView,
    NoticeDetailView,
    NoticeListView,
)

urlpatterns = [
    path("communities/", CommunityDirectoryView.as_view(), name="communities"),
    path("notices/", NoticeListView.as_view(), name="notices"),
    path("notices/<uuid:pk>/", NoticeDetailView.as_view(), name="notice-detail"),
    path("me/address-change/", AddressChangeView.as_view(), name="address-change"),
    path("me/address-change/cancel/", AddressChangeCancelView.as_view(), name="address-change-cancel"),
]
