from django.urls import path

from .views import CommunityDirectoryView, NoticeDetailView, NoticeListView

urlpatterns = [
    path("communities/", CommunityDirectoryView.as_view(), name="communities"),
    path("notices/", NoticeListView.as_view(), name="notices"),
    path("notices/<uuid:pk>/", NoticeDetailView.as_view(), name="notice-detail"),
]
