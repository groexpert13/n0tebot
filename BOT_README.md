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
- app/handlers/ai.py — обработчики текстовых и голосовых сообщений
- app/openai_client.py — асинхронный клиент для Responses API и транскрибации аудио
- app/logger.py — добавляет запись в `db.md` (секция `usage_log`)
- app/usage.py — best-effort обновление счётчиков в Supabase
- app/main.py — точка входа, регистрация роутеров и команд

6) Дальше

Когда пришлёте маппинг колонок/таблиц — добавим репозиторий/сервисы, middlewares и вызовы к Supabase. Также можно переключить на webhook + FastAPI при деплое.

7) Интеграция с OpenAI (Responses API + Whisper)

- Обновлённые зависимости: `openai>=1.30.0`, `aiofiles`.
- Новые файлы/модули:
  - `app/openai_client.py` — асинхронный клиент для Responses API и транскрибации аудио.
  - `app/handlers/ai.py` — обработчики текстовых и голосовых сообщений (распознаёт голос через Whisper и отправляет текст в модель).
  - `app/logger.py` — добавляет запись в `db.md` (секция `usage_log`) с полями: дата/время, tg_user_id, тип (`text`/`voice`), длительность голоса (сек), вход/выход/итого токены, модель.
  - `app/usage.py` — best-effort обновление счётчиков в Supabase (`app_users`: `text_tokens_used_total`, `text_generations_total`, `audio_minutes_total`, `audio_generations_total`).

Регистрация роутеров:

- `app/handlers/__init__.py` экспортирует `ai_router`.
- `app/main.py` включает `ai_router` в `Dispatcher`.

Поведение:

- Текст: любые сообщения без слеша (`/`) отправляются в модель, ответ — в чат; usage логируется.
- Голос: скачиваем OGG/OPUS, распознаём, отправляем распознанный текст в модель; в ответе показываем и транскрипт, и ответ; usage включает длительность аудио из Telegram.
- Видео-кружочки (`video_note`): скачиваем видео (mp4/webm), отправляем в распознавание (Whisper поддерживает видео-контейнеры), затем как голос — считаем в статистике как аудио.
- Пересланные сообщения: в подсказке модели добавляется префикс `[Forwarded from ...]` с инфо об исходном отправителе/чате.

Локальный запуск:

1. Установить зависимости: `pip install -r requirements.txt`
2. В `.env` добавить `OPENAI_API_KEY` и (опционально) `OPENAI_MODEL_TEXT`, `OPENAI_MODEL_TRANSCRIBE`.
3. Запустить: `python -m app.main`
