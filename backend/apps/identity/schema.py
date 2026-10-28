"""Описание способа входа для OpenAPI-схемы (по ней строится клиент для телефонов)."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class BearerAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.identity.authentication.BearerAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "description": "Токен доступа из /auth/code/verify/ или /auth/register/",
        }
