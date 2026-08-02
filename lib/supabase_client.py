from supabase import create_client, Client
from app.common import config

supabase: Client = create_client(
    config.SUPABASE.SUPABASE_URL, config.SUPABASE.SUPABASE_KEY
)


class NotFoundException(BaseException):
    pass
