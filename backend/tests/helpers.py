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


def register(api, token, building=None, **override):
    payload = {
        "registration_token": token,
        "display_name": "Анна Иванова",
        "is_adult": True,
        "consents": dict(settings.LEGAL_DOCUMENT_VERSIONS),
    }
    if building is not None:
        payload["building_id"] = str(building.id)
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


PASSWORD = "a-long-test-password-1"  # secret-scan: allow


def make_staff(email, communities=(), superuser=False):
    """Сотрудник: главный администратор или модератор, привязанный к ЖК (по slug)."""
    from django.core.management import call_command

    from apps.communities import roles
    from apps.communities.models import Community, ModeratorAssignment
    from apps.identity.models import User

    call_command("setup_roles")
    if superuser:
        return User.objects.create_superuser(email, password=PASSWORD)
    user = User.objects.create_user(email)
    roles.promote_to_moderator(user)
    for slug in communities:
        ModeratorAssignment.objects.create(user=user, community=Community.objects.get(slug=slug))
    return user


def admin_login(client, user):
    """Вход в админку с уже пройденной двухфакторной проверкой (саму проверку тестирует test_twofactor)."""
    from django.utils import timezone

    from apps.identity.twofactor import SESSION_KEY

    client.force_login(user)
    session = client.session
    session[SESSION_KEY] = timezone.now().isoformat()
    session.save()
    return client
