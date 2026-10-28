from django.urls import path

from .views import CommunityDirectoryView

urlpatterns = [path("communities/", CommunityDirectoryView.as_view(), name="communities")]
