from threading import Lock
from typing import Any

from supabase import Client, create_client
from app.common import config


class LazySupabaseClient:
    """Create the external client only when a database operation is requested.

    This keeps process startup and health checks independent from Supabase
    availability while preserving the existing ``supabase.table(...)`` API.
    """

    def __init__(self) -> None:
        self._client: Client | None = None
        self._lock = Lock()

    def _get_client(self) -> Client:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = create_client(
                        config.SUPABASE.SUPABASE_URL,
                        config.SUPABASE.SUPABASE_KEY,
                    )
        return self._client

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_client(), name)


supabase = LazySupabaseClient()


class NotFoundException(BaseException):
    pass
