| schema | table_name | column_name             | column_type              | is_nullable | column_default    |
| ------ | ---------- | ----------------------- | ------------------------ | ----------- | ----------------- |
| public | app_users  | id                      | uuid                     | NO          | gen_random_uuid() |
| public | app_users  | tg_user_id              | bigint                   | NO          | null              |
| public | app_users  | tg_username             | text                     | YES         | null              |
| public | app_users  | tg_first_name           | text                     | YES         | null              |
| public | app_users  | tg_last_name            | text                     | YES         | null              |
| public | app_users  | tg_language_code        | text                     | YES         | null              |
| public | app_users  | tg_is_premium           | boolean                  | YES         | null              |
| public | app_users  | tg_photo_url            | text                     | YES         | null              |
| public | app_users  | timezone                | text                     | NO          | 'UTC'::text       |
| public | app_users  | utc_offset_minutes      | smallint                 | YES         | null              |
| public | app_users  | web_language_code       | text                     | YES         | null              |
| public | app_users  | language_confirmed_at   | timestamp with time zone | YES         | null              |
| public | app_users  | privacy_accepted        | boolean                  | NO          | false             |
| public | app_users  | privacy_accepted_at     | timestamp with time zone | YES         | null              |
| public | app_users  | last_visit_at           | timestamp with time zone | YES         | null              |
| public | app_users  | visits_count            | integer                  | NO          | 0                 |
| public | app_users  | last_platform           | text                     | YES         | null              |
| public | app_users  | subscription_status     | text                     | YES         | 'none'::text      |
| public | app_users  | subscription_renew_at   | timestamp with time zone | YES         | null              |
| public | app_users  | text_tokens_used_total  | bigint                   | NO          | 0                 |
| public | app_users  | text_generations_total  | integer                  | NO          | 0                 |
| public | app_users  | audio_minutes_total     | integer                  | NO          | 0                 |
| public | app_users  | audio_generations_total | integer                  | NO          | 0                 |
| public | app_users  | stars_spent_total       | integer                  | NO          | 0                 |
| public | app_users  | created_at              | timestamp with time zone | NO          | now()             |
| public | app_users  | updated_at              | timestamp with time zone | NO          | now()             |
| public | notes      | id                      | uuid                     | NO          | gen_random_uuid() |
| public | notes      | user_id                 | uuid                     | NO          | null              |
| public | notes      | d                       | date                     | NO          | null              |
| public | notes      | title                   | text                     | YES         | null              |
| public | notes      | content                 | text                     | NO          | null              |
| public | notes      | source                  | text                     | YES         | 'web'::text       |
| public | notes      | time                    | time without time zone   | YES         | null              |
| public | notes      | created_at              | timestamp with time zone | NO          | now()             |
| public | notes      | updated_at              | timestamp with time zone | NO          | now()             |
| public | notes      | deleted_at              | timestamp with time zone | YES         | null              |
