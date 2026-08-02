import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from app.common import config


class SentryConfig:
    @staticmethod
    def init_sentry():
        """Initializes Sentry with FastAPI integration."""
        sentry_dsn = config.SENTRY.SENTRY_DSN
        sentry_env = config.SENTRY.SENTRY_ENV

        if sentry_dsn:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FastApiIntegration()],
                environment=sentry_env,
                sample_rate=0.2,
                send_default_pii=True,
            )
