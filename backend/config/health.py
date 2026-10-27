from django.db import connection
from django.http import JsonResponse

from .version import __version__


def health(request):
    """Проверка живости. Не раскрывает пути, настройки и данные."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:  # noqa: BLE001
        database = "error"
    status = 200 if database == "ok" else 503
    return JsonResponse(
        {"status": "ok" if database == "ok" else "degraded", "version": __version__, "database": database},
        status=status,
    )
