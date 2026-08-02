from datetime import datetime
from pydantic import BaseModel, EmailStr


class RoomJoinedUserReturn(BaseModel):
    email: EmailStr
    display_name: str
    room_code: str
    created_at: datetime
    status: str
    is_observer: bool
    truth: str | None
    objective: str | None
    nature: str | None


class ParticipantReturn(RoomJoinedUserReturn):
    pass


class ObserverReturn(RoomJoinedUserReturn):
    pass
