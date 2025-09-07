Бот на aiogram 3.x (Python)

Текущая версия: long polling, без запросов к Supabase (только инициализация клиента по env). Веб (Mini App) — отдельным проектом.

1) Переменные окружения

- `BOT_TOKEN` — токен Telegram-бота
- `SUPABASE_URL` — URL проекта Supabase
- `SUPABASE_SERVICE_ROLE_KEY` — Service Role Key

Пример — см. существующий `.env`. Для локального запуска значения подхватываются автоматически через python-dotenv.

2) Установка зависимостей

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

3) Запуск бота (long polling)

python -m app.main

Команды:

- /start — приветствие
- /help — помощь
- /ping — проверка ответа

4) Supabase

Клиент создаётся один раз при старте (если заданы `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY`) и кладётся в `Dispatcher.workflow_data["supabase"]`. До уточнения схемы таблиц никакие операции к БД не выполняются.

5) Структура

- app/config.py — чтение env
- app/supabase_client.py — ленивое создание клиента Supabase
- app/handlers/start.py — /start
- app/handlers/misc.py — /help, /ping
- app/main.py — точка входа, регистрация роутеров и команд

6) Дальше

Когда пришлёте маппинг колонок/таблиц — добавим репозиторий/сервисы, middlewares и вызовы к Supabase. Также можно переключить на webhook + FastAPI при деплое.

