# Деплой на Heroku (worker для Telegram polling)

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

5. Убедитесь, что dyno типа `worker` включён:
   `heroku ps:scale worker=1 --app <app-name>`

6. Просмотрите логи:
   `heroku logs --tail --app <app-name>`

Примечания:
- Проект запускает Telegram-bot через polling в worker-дино (Procfile). Если хотите использовать webhook, потребуется настроить вебсервер (Flask/FastAPI), expose URL и сертификат.
- Проверьте, что в Heroku установлена нужная версия Python (см. `runtime.txt`).
