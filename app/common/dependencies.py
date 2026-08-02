import logging
from typing import Annotated
from uuid import UUID
import json
import urllib.parse
import urllib.error
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from lib.supabase_client import supabase
from models.profile import Profile

logger = logging.getLogger("Dependencies")
security = HTTPBearer()


def extract_access_token(token: str) -> str:
    """
    Extract the access token from the full auth response.
    Handles both URL-encoded and raw JSON formats.
    """
    try:
        decoded = urllib.parse.unquote(token)
        try:
            auth_data = json.loads(decoded)
            if isinstance(auth_data, dict) and "access_token" in auth_data:
                return auth_data["access_token"]
        except json.JSONDecodeError:
            pass

        return decoded
    except (urllib.error.URLError, TypeError) as e:
        logger.error("Error decoding URL: %s", e)
        return token


async def get_current_profile(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """
    FastAPI dependency to get current session user from supabase.
    """
    try:
        access_token = extract_access_token(credentials.credentials)

        user = supabase.auth.get_user(access_token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid authentication token.")

        user_id = UUID(user.user.id)
        profile = Profile.fetch_by_id(user_id)
        if not profile:
            raise HTTPException(status_code=401, detail="Access token invalid.")
        return profile
    except Exception as exc:
        raise HTTPException(
            status_code=401, detail=f"Authentication error: {str(exc)}"
        ) from exc


async def admin_only(profile: Annotated[Profile, Depends(get_current_profile)]):
    """
    FastAPI dependency to validate admin endpoints.
    """
    if not profile.is_admin:
        raise HTTPException(
            status_code=403, detail="Not allowed. Admin access required."
        )
    return profile
