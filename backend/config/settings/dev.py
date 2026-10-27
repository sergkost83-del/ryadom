from .base import *  # noqa: F401,F403
from .base import env, env_list

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")  # secret-scan: allow
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
