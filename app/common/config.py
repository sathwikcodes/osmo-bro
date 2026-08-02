"""
Global app config
"""

from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True


class SentryConfig(BaseConfig):
    SENTRY_DSN: str = ""
    SENTRY_ENV: str = ""


class SupabaseConfig(BaseConfig):
    SUPABASE_URL: str
    SUPABASE_KEY: str


class OpenAIConfig(BaseConfig):
    OPENAI_API_KEY: str


class AIParticipantConfig(BaseConfig):
    AI_PARTICIPANT_DISPLAY_NAME: str = "AI Bot"
    AI_PARTICIPANT_EMAIL: str = "ai@example.com"


class Config(BaseConfig):
    ENVIRONMENT: str
    TESTING_MODE: bool = False
    EXTRA_MODELS_KEY: str
    SUPABASE: SupabaseConfig = SupabaseConfig()  # type: ignore
    SENTRY: SentryConfig = SentryConfig()
    OPENAI: OpenAIConfig = OpenAIConfig()  # type: ignore
    AIPARTICIPANT: AIParticipantConfig = AIParticipantConfig()  # type: ignore


config = Config()  # type: ignore
