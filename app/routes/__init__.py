from fastapi import APIRouter
from .room import router as room_router
from .message import router as message_router
from .profile import router as profile_router

router = APIRouter(tags=["health"])


@router.get(
    "/",
    summary="Health Check",
    description="Check if the API is running",
    response_description="Returns a message indicating the API is healthy",
)
async def check_health():
    """
    Health check endpoint to verify the API is running.

    Returns:
        dict: A message indicating the API is healthy
    """
    return {"message": "API is super healthy"}


ROUTES = [router, message_router, profile_router, room_router]
