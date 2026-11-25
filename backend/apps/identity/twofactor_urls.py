from django.urls import path

from . import twofactor_views as views

urlpatterns = [
    path("setup/", views.setup, name="twofactor-setup"),
    path("verify/", views.verify, name="twofactor-verify"),
    path("backup-codes/", views.backup_codes_page, name="twofactor-backup-codes"),
    path("backup-codes/regenerate/", views.regenerate_backup_codes, name="twofactor-backup-regenerate"),
]
