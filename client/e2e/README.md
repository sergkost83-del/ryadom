# Сквозной сценарий (браузер)

Тесты открывают приложение в Chromium, регистрируют двух соседей по кодам приглашения и проверяют переписку.

Запуск в CI — задание «Сквозной сценарий (браузер)». Локально в Codespaces:
1. В терминале сервера: `docker compose exec backend python manage.py seed_demo --out /tmp/ryadom-invites.json`
2. В другом терминале: `cd client/e2e && npm install && npx playwright install chromium && npx playwright test`
   (нужны запущенные сервер на 8000 и веб на 8081; адреса задаются `E2E_BASE_URL`)

Результаты: `reports/e2e-html` (с записью и скриншотами при падении).
