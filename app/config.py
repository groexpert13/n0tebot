import os
from dataclasses import dataclass
from typing import Optional


try:
    # Load .env for local development if present
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    # dotenv is optional in production environments
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    supabase_url: Optional[str]
    supabase_service_role_key: Optional[str]
    privacy_url: Optional[str]
    webapp_url: Optional[str]

    @staticmethod
    def from_env() -> "Settings":
        token = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN (or TELEGRAM_BOT_TOKEN) is not set in environment"
            )

        webapp_url = os.getenv("WEBAPP_URL")
        # Fix common typo like 'hhttps://'
        if webapp_url and webapp_url.startswith("hhttps://"):
            webapp_url = webapp_url.replace("hhttps://", "https://", 1)

        return Settings(
            bot_token=token,
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            privacy_url=os.getenv("PRIVACY_URL"),
            webapp_url=webapp_url,
        )


settings = Settings.from_env()
