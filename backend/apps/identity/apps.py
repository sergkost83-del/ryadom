from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "apps.identity"
    label = "identity"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import schema  # noqa: F401  (регистрирует описание авторизации для OpenAPI)
