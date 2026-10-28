from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.identity.models import EmailLoginCode, RefreshToken
from tests.helpers import last_code, request_code, signup, verify

pytestmark = pytest.mark.django_db


def test_attempt_limit_burns_the_code(api, settings):
    request_code(api, "a@example.com")
    good = last_code()
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(settings.AUTH_CODE_MAX_ATTEMPTS):
        assert verify(api, "a@example.com", wrong).status_code == 400
    assert verify(api, "a@example.com", good).status_code == 400


def test_code_is_single_use(api):
    request_code(api, "u@example.com")
    code = last_code()
    assert verify(api, "u@example.com", code).status_code == 200
    assert verify(api, "u@example.com", code).status_code == 400


def test_expired_code_is_rejected(api):
    request_code(api, "e@example.com")
    code = last_code()
    EmailLoginCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert verify(api, "e@example.com", code).status_code == 400


def test_code_for_another_email_is_rejected(api):
    request_code(api, "mine@example.com")
    assert verify(api, "other@example.com", last_code()).status_code == 400


def test_resend_cooldown_sends_one_mail(api):
    assert request_code(api, "r@example.com").status_code == 202
    assert request_code(api, "r@example.com").status_code == 202
    assert len(mail.outbox) == 1


def test_request_limit_per_email(api, settings):
    settings.AUTH_CODE_RESEND_SECONDS = 0
    for _ in range(settings.AUTH_REQUESTS_PER_EMAIL_HOUR):
        assert request_code(api, "l@example.com").status_code == 202
    response = request_code(api, "l@example.com")
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0


def test_request_limit_per_ip_across_emails(api, settings):
    for i in range(settings.AUTH_REQUESTS_PER_IP_HOUR):
        assert request_code(api, f"user{i}@example.com").status_code == 202
    assert request_code(api, "one-more@example.com").status_code == 429


def test_verify_limit_per_email(api, settings):
    for _ in range(settings.AUTH_VERIFY_PER_EMAIL_HOUR):
        assert verify(api, "v@example.com", "123456").status_code == 400
    assert verify(api, "v@example.com", "123456").status_code == 429


def test_request_does_not_reveal_whether_email_is_registered(api, building):
    signup(api, "known@example.com", building)
    known = request_code(api, "known@example.com")
    unknown = request_code(api, "unknown@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_codes_and_tokens_are_not_stored_in_plain_text(api, building):
    request_code(api, "plain@example.com")
    code = last_code()
    assert all(code not in row.code_hash for row in EmailLoginCode.objects.all())
    tokens = signup(api, "plain2@example.com", building)["tokens"]
    stored = list(RefreshToken.objects.values_list("token_hash", flat=True))
    assert tokens["refresh"] not in stored


def test_malformed_input_is_rejected(api):
    assert request_code(api, "not-an-email").status_code == 400
    assert verify(api, "a@example.com", "12ab56").status_code == 400
    assert verify(api, "a@example.com", "12345").status_code == 400
