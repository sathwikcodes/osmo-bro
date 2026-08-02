import logging
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Body, status
from openai import OpenAI
from app.common import config
from models import MediatorType
from lib.exceptions import BadRequest
from lib.schema import (
    CreateRoom,
    CreateParticipant,
    RemoveParticipant,
    RoomReturn,
    RoomDetailResponse,
    CreateMessage,
)
from models import Room, Profile, Participant
from core import HandleIncomingMessage, MediationFlow, RoomManager
from app.common.dependencies import get_current_profile


router = APIRouter(
    prefix="/room",
    tags=["rooms"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    },
)
OPENAI_API_KEY = config.OPENAI.OPENAI_API_KEY
AI_PARTICIPANT = config.AIPARTICIPANT.AI_PARTICIPANT_DISPLAY_NAME

client = OpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger("Room")


def analyze_image(image_url: str) -> str:
    """
    Analyze an image using GPT-4 Vision and return the analysis.
    """
    try:
        logger.info("Starting image analysis for URL: %s", image_url)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze this image and describe its contents in detail. 
                            Focus on any text, objects, or relevant information that could be important 
                            for conflict resolution.""",
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=500,
        )
        content = response.choices[0].message.content
        logger.info("Image analysis completed: %s", content)
        return content if content is not None else "No analysis available."
    except Exception as e:
        logger.error("Error analyzing image: %s", e)
        return "Error analyzing image. Please try again."


@router.get(
    "/",
    response_model=List[RoomReturn],
    summary="Get All Rooms",
    description="Get a list of all rooms. Only accessible by admin users.",
    status_code=status.HTTP_200_OK,
)
async def get_all_rooms():
    """
    Get all rooms in the system.

    This endpoint requires admin privileges.
    """
    rooms = Room.fetch_all()
    return [room.model_dump() for room in rooms]


@router.get(
    "/me",
    response_model=List[RoomReturn],
    summary="Get My Rooms",
    description="Get a list of rooms associated with the current user.",
    status_code=status.HTTP_200_OK,
)
async def get_my_rooms(profile: Annotated[Profile, Depends(get_current_profile)]):
    """
    Get all rooms associated with the current user.
    """
    rooms = Room.fetch_rooms_for_profile(profile.email)
    return [room.model_dump() for room in rooms]


@router.get(
    "/{room_code}",
    response_model=RoomDetailResponse,
    summary="Get Room Details",
    description="Get detailed information about a specific room.",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Room not found"},
        400: {"description": "Not a parent room"},
    },
)
async def get_room(room_code: str):
    """
    Get detailed information about a specific room.

    Parameters:
        room_code: The unique code of the room
    """
    room = Room.fetch_by_room_code(room_code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found with given room code.",
        )

    if room.parent_room_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a parent room."
        )

    room_joined_users = room.participants(include_observers=True)
    breakout_rooms = room.get_breakout_rooms()

    breakout_rooms_data = {
        email: room_data.model_dump() for email, room_data in breakout_rooms.items()
    }

    return {
        "room": room.model_dump(),
        "participants": [
            participant.model_dump()
            for participant in room_joined_users
            if participant.is_observer is False
        ],
        "observers": [
            observer.model_dump()
            for observer in room_joined_users
            if observer.is_observer is True
        ],
        "breakout_rooms": breakout_rooms_data,
    }


@router.post(
    "/initialise",
    response_model=RoomDetailResponse,
    summary="Initialize New Room",
    description="Create and initialize a new room with participants and observers.",
    status_code=status.HTTP_201_CREATED,
)
async def initialise_room(create_room: CreateRoom):
    """
    Initialize a new room with participants and observers. Initialise AI Bot conversation in background, separate from the human conversations.
    """
    try:
        data = Room.create(create_room)

        participants = data["participants"]
        breakout_rooms = data["breakout_rooms"]
        observers = data["observers"]

        breakout_room_map = {br["creator_email"]: br for br in breakout_rooms}
        ai_display_name = RoomManager.sanitize_display_name(AI_PARTICIPANT)

        ai_participant = None
        human_participants = []
        non_ai_breakout_rooms = []

        for participant in participants:
            sanitized_name = RoomManager.sanitize_display_name(
                participant.profile.display_name
            )

            if sanitized_name == ai_display_name:
                ai_participant = participant
            else:
                human_participants.append(participant)
                br = breakout_room_map.get(participant.email)
                if br:
                    non_ai_breakout_rooms.append(br)

        for br in non_ai_breakout_rooms:
            try:
                await MediationFlow.initialise_caucus(room=Room(**br))
            except Exception as e:
                logger.error("Error initializing human participant room: %s", e)

        if ai_participant:
            ai_br_data = breakout_room_map.get(ai_participant.email)
            if ai_br_data:
                await HandleIncomingMessage.initialize_ai_bot_conversation(
                    room=Room(**ai_br_data)
                )

        breakout_rooms_dict = {
            email: RoomReturn(**br) for email, br in breakout_room_map.items()
        }

        return {
            "room": data["room"].model_dump(),
            "participants": [p.model_dump() for p in participants],
            "observers": [o.model_dump() for o in observers],
            "breakout_rooms": breakout_rooms_dict,
        }

    except Exception as e:
        raise BadRequest(message=f"Failed to initialize room: {str(e)}") from e


@router.get("/{room_code}/conversations")
async def get_room_conversations(room_code: str):
    """
    Route to get room conversations.
    """
    room = Room.fetch_by_room_code(room_code)
    if not room:
        raise HTTPException(
            status_code=404, detail="Room not found with given room code."
        )

    conversations = room.get_conversation()
    return [conversation.model_dump() for conversation in conversations.messages]


@router.get("/{room_code}/participant/{email}")
async def get_room_participant(room_code: str, email: str):
    """
    Route to get room participant.
    """
    participant = Participant.fetch_by_room_code_and_email(
        room_code=room_code, email=email
    )
    if not participant:
        raise HTTPException(
            status_code=404, detail="Participant not found with room_code and email."
        )
    return participant.model_dump()


@router.post("/{room_code}/participant")
async def add_room_participant(
    room_code: str,
    create_participant: CreateParticipant,
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """
    Route to add participant to room.
    """
    room = Room.fetch_by_room_code_and_creator_email(room_code, profile.email)
    return Participant.create(
        room_code=room.room_code,
        create_participant=create_participant,
    ).model_dump()


@router.delete("/{room_code}/participant")
async def remove_room_participant(
    room_code: str,
    remove_participant: RemoveParticipant,
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """
    Route to remove participant from room.
    """
    room = Room.fetch_by_room_code_and_creator_email(room_code, profile.email)
    Participant.remove(
        room_code=room.room_code,
        email=remove_participant.email,
    )
    return {}


@router.get("/{room_code}/get_conflict_type")
async def get_conflict_type(room_code: str):
    """
    Route to fetch the conflict type of the Room.
    """
    room = Room.fetch_by_room_code(room_code=room_code)
    room = room.get_parent_room() or room
    return {"conflict_type": room.mediator_type}


@router.post("/{room_code}/change_conflict_type")
async def change_conflict_type(
    room_code: str, conflict_type: MediatorType = Body(..., embed=True)
):
    """
    Route to change the conflict type of the Room.
    """
    room = Room.fetch_by_room_code(room_code=room_code)
    room = room.get_parent_room() or room
    room.update_mediator_type(conflict_type)
    return {"room": room.room_code, "conflict_type": room.mediator_type}


@router.get("/{room_code}/get_status")
async def get_status(room_code: str):
    """
    Route to fetch the status of the Room.
    """
    room = Room.fetch_by_room_code(room_code=room_code)
    room = room.get_parent_room() or room
    return {"status": room.status}


@router.post("/{room_code}/message")
async def post_message(
    room_code: str,
    create_message: CreateMessage,
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """
    Handle new message creation, including image processing if present.
    """
    room = Room.fetch_by_room_code_and_creator_email(
        room_code=room_code, email=profile.email
    )
    if not room:
        raise HTTPException(
            status_code=404,
            detail="Room not found with given room code and creator email.",
        )

    if create_message.has_image and create_message.image_url:
        image_analysis = analyze_image(create_message.image_url)
        create_message.image_analysis = image_analysis

    try:
        response = await HandleIncomingMessage.handle_new_message(
            profile=profile,
            room=room,
            create_message=create_message,
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
            status_code=400, detail=f"Failed to process message: {str(e)}"
        ) from e


@router.get("/{room_code}/breakout_rooms")
async def get_breakout_rooms_details(
    room_code: str, profile: Annotated[Profile, Depends(get_current_profile)]
):
    """
    Fetch breakout room details for the logged-in user.
    """
    room = Room.fetch_by_room_code(room_code)
    if not room:
        raise HTTPException(
            status_code=404, detail="Room not found with given room code."
        )

    breakout_rooms = room.get_breakout_rooms()
    breakout_room_for_user = breakout_rooms.get(profile.email)
    if not breakout_room_for_user:
        raise HTTPException(
            status_code=404, detail="Breakout room not found for the user."
        )

    return breakout_room_for_user.model_dump()
