"""
Util file containing useful decorators.
"""

from typing import Type, TypeVar, Callable
from uuid import UUID
from fastapi import Request, HTTPException, Depends
from pydantic import BaseModel
from lib.supabase_client import supabase
from models.profile import Profile

T = TypeVar("T", bound=BaseModel)


def response_model(schema: Type[T]) -> Callable:
    """Decorator to validate response data with a Pydantic model."""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> T:
            result = await func(*args, **kwargs)
            return schema(**result)

        return wrapper

    return decorator


async def get_current_user(request: Request) -> Profile:
    """
    Dependency to get current session user from supabase.
    """
    authorization = request.headers.get("Authorization")

    if not authorization or "Bearer " not in authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        jwt = authorization.split(" ")[1]
        user_response = supabase.auth.get_user(jwt)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid user token")
        user_id = user_response.user.id
        profile = Profile.fetch_by_id(UUID(user_id))
        if not profile:
            raise HTTPException(status_code=401, detail="Access token invalid")

        return profile
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def verify_admin(profile: Profile = Depends(get_current_user)):
    """
    Dependency to validate admin access.
    """
    if not profile.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")
    return profile
