import base64
import hashlib

from .base import *  # noqa: F401,F403
from .base import FIELD_ENCRYPTION_KEYS, env, env_list

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")  # secret-scan: allow
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
if not FIELD_ENCRYPTION_KEYS:  # ключ только для локальной разработки
    FIELD_ENCRYPTION_KEYS = [base64.urlsafe_b64encode(hashlib.sha256(b"ryadom-dev-only").digest()).decode()]
