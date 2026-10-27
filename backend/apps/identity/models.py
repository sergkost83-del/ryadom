import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email(value):
    """Единый вид e-mail: без пробелов по краям и в нижнем регистре."""
    return (value or "").strip().lower()


class UserManager(BaseUserManager):
    def _create(self, email, password, **extra):
        email = normalize_email(email)
        if not email:
            raise ValueError("Нужен e-mail.")
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if not password:
            raise ValueError("Для администратора нужен пароль.")
        if not (extra["is_staff"] and extra["is_superuser"]):
            raise ValueError("Администратор должен иметь is_staff и is_superuser.")
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Аккаунт жителя или сотрудника. Жители входят по коду из e-mail, пароля у них нет."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(email=Lower("email")), name="identity_user_email_lowercase"),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
