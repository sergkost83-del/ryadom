import pytest
from django.core.management import call_command

# makemigrations --check сверяет историю миграций с базой, поэтому доступ к базе обязателен.
pytestmark = pytest.mark.django_db


def test_no_model_changes_without_migration():
    try:
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)
    except SystemExit:
        pytest.fail("Модели изменены без миграции: выполните makemigrations и закоммитьте файл.")
