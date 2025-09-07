# Деплой на Heroku (webhook или polling)

Шаги (локально):

1. Войдите в Heroku: `heroku login`
2. Создайте приложение: `heroku create <app-name>`
3. Установите переменные окружения (config vars) в Heroku, например:
   - BOT_TOKEN
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY
   - WEBAPP_URL
   - PRIVACY_URL

   Используйте: `heroku config:set BOT_TOKEN=xxxx SUPABASE_URL=... --app <app-name>`

4. Запушьте в Heroku (если remote ещё не создан):
   `git push https://git.heroku.com/<app-name>.git main`

5. Включите нужные dyno:
   - Webhook-режим (рекомендуется в проде):
     - включите web: `heroku ps:scale web=1 --app <app-name>`
     - отключите worker: `heroku ps:scale worker=0 --app <app-name>`
   - Polling-режим (простой старт):
     - включите worker: `heroku ps:scale worker=1 --app <app-name>`
     - можно отключить web: `heroku ps:scale web=0 --app <app-name>`

6. Просмотрите логи:
   `heroku logs --tail --app <app-name>`

## Webhook Telegram

В проект добавлен FastAPI-эндпоинт `POST /telegram/webhook`, который принимает обновления Telegram и прокидывает их в aiogram.

1) Установите секрет (опционально, но лучше включить):

```
heroku config:set TELEGRAM_WEBHOOK_SECRET=<случайная_строка> --app <app-name>
```

2) Включите web-дино и отключите polling:

```
heroku ps:scale web=1 worker=0 --app <app-name>
```

3) Зарегистрируйте webhook у Telegram:

```
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://<app-name>.herokuapp.com/telegram/webhook",
        "secret_token": "'$TELEGRAM_WEBHOOK_SECRET'"
      }'
```

4) Проверка:

```
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

Если нужно отключить webhook и вернуться на polling:

```
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook"
heroku ps:scale worker=1 web=0 --app <app-name>
```

Примечания:
- Telegram присылает заголовок `X-Telegram-Bot-Api-Secret-Token`; если переменная `TELEGRAM_WEBHOOK_SECRET` задана, эндпоинт проверяет точное совпадение и отклоняет чужие запросы.
- Проверьте, что в Heroku установлена нужная версия Python (см. `runtime.txt`).
