from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr, Field
from models.mediator_type import MediatorType


class CreateRoom(BaseModel):
    """
    Schema for creating a new room.
    """

    room_name: str = Field(..., description="Name of the room")
    creator_email: EmailStr = Field(..., description="Email of the room creator")
    mediator_type: MediatorType = Field(
        ..., description="Type of mediator for the room"
    )
    parent_room_code: Optional[str] = Field(
        None, description="Code of the parent room if this is a breakout room"
    )
    description: str = Field(..., description="Description of the room and conflict")
    participants: List[str] = Field(
        default=[], description="List of participant email addresses"
    )
    observers: List[str] = Field(
        default=[], description="List of observer email addresses"
    )
    objective: Optional[str] = Field(
        default=None, description="The main goal or desired outcome of the room"
    )
    truth: Optional[str] = Field(
        default=None,
        description="Statements or facts considered central to the discussion",
    )
    nature: Optional[str] = Field(
        default=None, description="Underlying nature or type of the conflict"
    )


class RoomReturn(BaseModel):
    """
    Schema for room details returned by the API.
    """

    room_code: str = Field(..., description="Unique code identifying the room")
    room_name: str = Field(..., description="Name of the room")
    creator_email: EmailStr = Field(..., description="Email of the room creator")
    status: str = Field(..., description="Current status of the room")
    created_at: datetime = Field(..., description="When the room was created")
    updated_at: Optional[datetime] = Field(
        None, description="When the room was last updated"
    )
    mediator_type: MediatorType = Field(
        ..., description="Type of mediator for the room"
    )
    parent_room_code: Optional[str] = Field(
        None, description="Code of the parent room if this is a breakout room"
    )
    description: str = Field(..., description="Description of the room and conflict")
    completed_iterations: Optional[int] = Field(
        None, description="Number of completed mediation iterations"
    )


class ParticipantReturn(BaseModel):
    """
    Schema for participant details returned by the API.
    """

    email: EmailStr = Field(..., description="Email of the participant")
    display_name: str = Field(..., description="Display name of the participant")
    room_code: str = Field(..., description="Room code the participant belongs to")
    created_at: datetime = Field(..., description="When the participant was added")
    status: str = Field(..., description="Current status of the participant")
    is_observer: bool = Field(
        ..., description="Whether this participant is an observer"
    )
    truth: Optional[str] = Field(
        None, description="Participant's perspective of the truth"
    )
    objective: Optional[str] = Field(
        None, description="Participant's objective in the mediation"
    )
    nature: Optional[str] = Field(
        None, description="Nature/behavior of the participant"
    )


class RoomDetailResponse(BaseModel):
    """
    Schema for detailed room information including participants and breakout rooms.
    """

    room: RoomReturn = Field(..., description="Main room details")
    participants: List[ParticipantReturn] = Field(
        ..., description="List of active participants"
    )
    observers: List[ParticipantReturn] = Field(..., description="List of observers")
    breakout_rooms: Dict[str, RoomReturn] = Field(
        ..., description="Mapping of breakout rooms by email"
    )


class CreateParticipant(BaseModel):
    """
    Schema for adding a new participant to a room.
    """

    email: EmailStr = Field(..., description="Email of the participant to add")
    is_observer: bool = Field(default=True, description="Whether to add as an observer")


class RemoveParticipant(BaseModel):
    """
    Schema for removing a participant from a room.
    """

    email: EmailStr = Field(..., description="Email of the participant to remove")
