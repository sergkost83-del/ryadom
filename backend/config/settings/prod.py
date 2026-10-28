"""Боевые настройки. Без обязательных переменных окружения сервер не стартует."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS, SECRET_KEY, env, env_bool

DEBUG = False

if not SECRET_KEY or len(SECRET_KEY) < 50 or SECRET_KEY.startswith("insecure"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY обязателен: не короче 50 символов, не 'insecure…'.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS обязателен (через запятую).")

if not env("EMAIL_HOST"):
    raise ImproperlyConfigured("EMAIL_HOST обязателен: без почты не работает вход по коду.")

# За прокси (Caddy/nginx) IP клиента берём из X-Forwarded-For; без этого лимиты считались бы по IP прокси.
TRUSTED_PROXY_COUNT = int(env("TRUSTED_PROXY_COUNT", "1"))

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_REFERRER_POLICY = "same-origin"
if env_bool("DJANGO_BEHIND_PROXY", True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# В список предзагрузки HSTS домен не подаём, пока домен не утверждён.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
