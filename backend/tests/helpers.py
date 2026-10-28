import re

from rest_framework.test import APIClient

from django.conf import settings
from django.core import mail

CODE_RE = re.compile(r"\b(\d{6})\b")
URL = "/api/v1/"


def last_code():
    return CODE_RE.search(mail.outbox[-1].body).group(1)


def request_code(api, email):
    return api.post(URL + "auth/code/request/", {"email": email}, format="json")


def verify(api, email, code, **extra):
    return api.post(URL + "auth/code/verify/", {"email": email, "code": code, **extra}, format="json")


def verified_token(api, email):
    """Проходит запрос и подтверждение кода для нового e-mail, возвращает токен регистрации."""
    request_code(api, email)
    response = verify(api, email, last_code())
    assert response.status_code == 200, response.content
    return response.json()["registration_token"]


def register(api, token, building, **override):
    payload = {
        "registration_token": token,
        "display_name": "Анна Иванова",
        "is_adult": True,
        "consents": dict(settings.LEGAL_DOCUMENT_VERSIONS),
        "building_id": str(building.id),
    }
    payload.update(override)
    return api.post(URL + "auth/register/", payload, format="json")


def signup(api, email, building, **override):
    response = register(api, verified_token(api, email), building, **override)
    assert response.status_code == 201, response.content
    return response.json()


def login(api, email, **extra):
    """Вход существующего пользователя по коду. Возвращает ответ verify."""
    request_code(api, email)
    return verify(api, email, last_code(), **extra)


def as_user(client, access):
    client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    return client


def client_for(tokens):
    """Отдельный клиент с токеном конкретного пользователя."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    return client


def resident(api, email, building, status="confirmed", **override):
    """Регистрирует жителя и выставляет статус адреса (как это сделал бы модератор)."""
    from apps.communities.models import Membership

    tokens = signup(api, email, building, **override)["tokens"]
    Membership.objects.filter(user__email=email).update(status=status)
    return client_for(tokens)
