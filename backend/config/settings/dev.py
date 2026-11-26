import base64
import hashlib

from .base import *  # noqa: F401,F403
from .base import FIELD_ENCRYPTION_KEYS, env, env_list

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")  # secret-scan: allow
# Адреса GitHub Codespaces (…app.github.dev) и localhost. Только для разработки.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]", ".app.github.dev"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", ["https://*.app.github.dev", "http://localhost:8081"])
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_FILE_PATH = env("EMAIL_FILE_PATH", "/tmp/ryadom-mail")  # для сквозного сценария письма пишутся в файлы

# Разрешаем запросы из браузера с другого адреса (приложение Expo на другом порту). Только в разработке.
INSTALLED_APPS = [*INSTALLED_APPS, "corsheaders"]  # noqa: F405
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", *MIDDLEWARE]  # noqa: F405
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.app\.github\.dev$",
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
CORS_ALLOW_CREDENTIALS = False

if not FIELD_ENCRYPTION_KEYS:  # ключ только для локальной разработки
    FIELD_ENCRYPTION_KEYS = [base64.urlsafe_b64encode(hashlib.sha256(b"ryadom-dev-only").digest()).decode()]
