"""
Supabase DB client
"""

from supabase import create_client, Client
from app.common import config

db: Client = create_client(config.SUPABASE.SUPABASE_URL, config.SUPABASE.SUPABASE_KEY)
