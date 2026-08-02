from typing import List, Annotated
from fastapi import APIRouter, Depends
from models import Profile
from app.common.dependencies import admin_only

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=List[dict])
async def get_all_profiles(profile: Annotated[Profile, Depends(admin_only)]):
    """
    Route to get all profiles.
    """
    profiles = Profile.fetch_all()
    return [profile.model_dump() for profile in profiles]
