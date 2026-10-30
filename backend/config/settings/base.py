"""Базовые настройки РЯДОМ. Секреты и адреса берутся только из переменных окружения."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.version import __version__

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name, default=None):
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    value = env(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

ADMIN_URL = env("ADMIN_URL", "admin/")
if not ADMIN_URL.endswith("/") or ADMIN_URL.startswith("/"):
    raise ImproperlyConfigured("ADMIN_URL должен быть вида 'panel-x7/' (без начального '/', с конечным '/').")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.identity",
    "apps.communities",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.identity.middleware.AdminTwoFactorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "ryadom"),
        "USER": env("POSTGRES_USER", "ryadom"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
    }
}

AUTH_USER_MODEL = "identity.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Ограничение размера тела запроса (защита от перегрузки): 1 МиБ.
DATA_UPLOAD_MAX_MEMORY_SIZE = 1_048_576
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# По умолчанию API закрыт: без токена доступ запрещён; открытые адреса помечаются явно.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.identity.authentication.BearerAuthentication"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "600/min"},
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "РЯДОМ API",
    "VERSION": __version__,
    "SERVE_INCLUDE_SCHEMA": False,
}

# В журналах не должно быть персональных данных: тела запросов не логируем.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

# --- Вход по коду из e-mail и сессии ---
AUTH_CODE_TTL_SECONDS = 600
AUTH_CODE_MAX_ATTEMPTS = 5
AUTH_CODE_RESEND_SECONDS = 60
AUTH_REQUESTS_PER_EMAIL_HOUR = 5
AUTH_REQUESTS_PER_IP_HOUR = 20
AUTH_VERIFY_PER_EMAIL_HOUR = 10
AUTH_VERIFY_PER_IP_HOUR = 60
AUTH_REGISTRATION_TTL_SECONDS = 900
AUTH_ACCESS_TTL_SECONDS = 900
AUTH_REFRESH_TTL_DAYS = 60
# Сколько прокси стоит перед сервером (для определения IP клиента по X-Forwarded-For).
TRUSTED_PROXY_COUNT = int(env("TRUSTED_PROXY_COUNT", "0"))

# Версии юридических документов. Меняются только вместе с публикацией нового текста (после проверки юристом).
LEGAL_DOCUMENT_VERSIONS = {"privacy_policy": "2026-10-draft", "personal_data": "2026-10-draft"}
MINIMUM_AGE = 18
# Срок между запросом на удаление и окончательным стиранием данных. Предварительно: утвердить с юристом.
ACCOUNT_ERASURE_DAYS = 30

# --- Админка: двухфакторная защита обязательна для всех сотрудников ---
ADMIN_2FA_SESSION_HOURS = 12
SESSION_COOKIE_AGE = ADMIN_2FA_SESSION_HOURS * 3600
ADMIN_2FA_ATTEMPTS_PER_15_MIN = 10
BACKUP_CODES_COUNT = 10

# --- Коды приглашения домов ---
INVITE_DEFAULT_DAYS = 14
INVITE_MAX_DAYS = 60
INVITE_ATTEMPTS_PER_IP_HOUR = 10

# --- Почта ---
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "РЯДОМ <no-reply@localhost>")
