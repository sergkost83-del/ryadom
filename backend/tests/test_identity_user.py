import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.identity.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email_and_has_no_password():
    user = User.objects.create_user("  Anna@Example.COM ")
    assert user.email == "anna@example.com"
    assert not user.has_usable_password()
    assert isinstance(user.id, uuid.UUID)
    assert user.is_active and not user.is_staff and not user.is_superuser


def test_email_is_unique_regardless_of_case():
    User.objects.create_user("a@example.com")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user("A@EXAMPLE.com")


def test_database_rejects_uppercase_email_even_if_save_is_bypassed():
    user = User.objects.create_user("b@example.com")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.filter(pk=user.pk).update(email="UPPER@example.com")


def test_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user("   ")


def test_superuser_requires_password_and_flags():
    with pytest.raises(ValueError):
        User.objects.create_superuser("root@example.com", password=None)
    password = "a-long-test-password-1"  # secret-scan: allow
    admin = User.objects.create_superuser("root@example.com", password=password)
    assert admin.is_staff and admin.is_superuser and admin.check_password(password)
