from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from core import HandleIncomingMessage
from lib.schema import CreateMessage
from app.common.dependencies import get_current_profile, require_room_access
from models.room import Profile, Room

router = APIRouter(prefix="/message", tags=["message"])


@router.post("/send")
async def send_message(
    create_message: CreateMessage,
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """
    Handle sending a new message.
    """
    try:
        room = require_room_access(create_message.room_code, profile)

        response = await HandleIncomingMessage.handle_new_message(
            profile=profile, room=room, create_message=create_message
        )
        return {
            "id": str(response.message_id),
            "content": response.content,
            "email": response.email,
            "role": response.role,
            "created_at": response.created_at.isoformat(),
            "has_image": create_message.has_image,
            "image_url": create_message.image_url,
            "image_analysis": (
                create_message.image_analysis if create_message.has_image else None
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Failed to send message: {str(e)}"
        ) from e
