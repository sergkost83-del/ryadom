import uuid

from django.conf import settings
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
    avatar_id = models.PositiveSmallIntegerField(default=1)
    phone = models.CharField(max_length=20, blank=True)
    # Тип аккаунта расширяемый: сейчас только взрослые (18+). Другие категории — после правовой проработки.
    account_type = models.CharField(max_length=20, default="adult")
    age_confirmed_at = models.DateTimeField(null=True, blank=True)
    # Заполняется при запросе на удаление; окончательное стирание — через ACCOUNT_ERASURE_DAYS.
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
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


class EmailLoginCode(models.Model):
    """Одноразовый код входа. Сам код не хранится, только HMAC-хэш."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["email", "created_at"], name="identity_code_email_created")]


class AuthThrottle(models.Model):
    """Счётчик попыток за окно времени. Ключ — хэш (e-mail и IP в открытом виде не хранятся)."""

    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField()


class Session(models.Model):
    """Вход с одного устройства. Отзыв сессии мгновенно закрывает доступ."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    device_name = models.CharField(max_length=60, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)


class RefreshToken(models.Model):
    """Токен обновления одноразовый: после использования выдаётся новый, повтор старого отзывает сессию."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class Consent(models.Model):
    """Принятое согласие/политика с версией документа и временем."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consents")
    consent_type = models.CharField(max_length=30)
    version = models.CharField(max_length=40)
    accepted_at = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "consent_type", "version"], name="identity_consent_unique"),
        ]


class TOTPDevice(models.Model):
    """Приложение-аутентификатор сотрудника. Подтверждённое устройство обязательно для входа в админку."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp_device")
    secret = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_step = models.BigIntegerField(null=True, blank=True)


class BackupCode(models.Model):
    """Резервный код восстановления (одноразовый). Хранится только хэш."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True, blank=True)
