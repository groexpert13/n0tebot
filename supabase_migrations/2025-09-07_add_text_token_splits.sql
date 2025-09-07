-- Adds separate counters for input and output text tokens.
-- Safe to run multiple times due to IF NOT EXISTS guards.

alter table if exists public.app_users
    add column if not exists text_input_tokens_total bigint not null default 0;

alter table if exists public.app_users
    add column if not exists text_output_tokens_total bigint not null default 0;

-- Note on audio counters:
-- The existing column public.app_users.audio_minutes_total is used to store SECONDS
-- of audio/video notes (by design decision), despite the misleading name.
-- Consider a follow-up migration to rename the column to audio_seconds_total
-- when convenient:
--   alter table public.app_users rename column audio_minutes_total to audio_seconds_total;
