"""
This module deals with the "room" (Room) and "room_joined_users" (Participant) tables in the database.
"""

from enum import Enum
from uuid import UUID
from typing import Optional
from collections.abc import Sequence
from pydantic import BaseModel, Field, EmailStr, PastDatetime, AwareDatetime
from models.base import BaseSupabaseModel
from models.conversation import Conversation
from models.profile import Profile
from models.mediator_type import MediatorType
from lib.utils import model, generate_room_code
from app.common import config
from lib.schema import CreateRoom, CreateParticipant
from lib.exceptions import NotFound


class Status(str, Enum):
    """
    Flags to indicate the status of a participant in a room.
    Corresponds to the "status" field in the "room_joined_users" table.
    Used to control the flow of the mediation process
    """

    INIT = "init"
    IN_CAUCUS = "in_caucus"
    AWAITING_MEDIATION = "awaiting_mediation"
    IN_MEDIATION = "in_mediation"
    MEDIATION_DONE = "mediation_done"
    SATISFIED = "satisfied"
    RESOLVED = "resolved"
    NO_RESOLUTION = "no_resolution"


class RoomStatus(str, Enum):
    """
    Global status of a room
    Corresponds to the "status" field in the "rooms" table
    Can be used to implement a multi-stage mediation process,
    and also to track the progress of a room when scaled.
    """

    MEDIATION = "in_mediation"
    RESOLVED = "resolved"
    NO_RESOLUTION = "no_resolution"


@model(table_name="room_joined_users")
class Participant(BaseModel, BaseSupabaseModel):
    """
    This model corresponds to the "room_joined_users" table in the database.
    Each row/instance in the table represents a participant in a room.
    The model provides methods to fetch, update and set the status of a participant in a room.
    """

    participant_id: UUID = Field(alias="id")
    email: EmailStr
    display_name: str
    room_code: str
    created_at: AwareDatetime
    status: Status
    is_observer: bool = False
    truth: Optional[str]
    objective: Optional[str]
    nature: Optional[str]

    @classmethod
    def fetch_for_room(cls, room: "Room"):
        """
        Fetches all participants in a room
        """
        parent_room: "Room" = room.get_parent_room() or room
        return cls._fetch_by_key_value("room_code", parent_room.room_code)

    @classmethod
    def fetch_for_room_email(cls, room: "Room", email: str):
        """
        Fetches a participant in a room by email
        """
        parent_room: "Room" = room.get_parent_room() or room
        matches = cls._from_api_response(
            (
                cls.get_table()
                .select("*")
                .eq("room_code", parent_room.room_code)
                .eq("email", email)
                .limit(1)
                .execute()
            )
        )
        if not matches:
            raise NotFound(message="Room-email combination not found")
        return matches[0]

    @property
    def profile(self) -> Profile:
        """
        Fetches the profile of the participant and caches it
        """
        if hasattr(self, "_profile"):
            return self._profile
        self._profile = Profile.fetch_by_email(self.email)
        return self._profile

    @property
    def room(self) -> "Room":
        """
        Fetches the room of the participant and caches it
        """
        if hasattr(self, "_room"):
            return self._room
        self._room = Room.fetch_by_room_code(self.room_code)
        return self._room

    def update_status(self, status: Status):
        """
        Probably one of the most important methods in this class.
        Updates the status of a participant in a room.
        Used to control the flow of the mediation process.
        """
        if status == self.status:
            return
        self.status = status
        self.get_table().update({"status": self.status}).eq(
            "id", self.participant_id
        ).execute()

    def set_perspective(self, truth: str, objective: str, nature: str):
        """
        Sets the perspective of a participant in a room.
        """
        self.truth = truth
        self.objective = objective
        self.nature = nature

        # Update using Supabase client
        self.get_table().update(
            {"truth": truth, "objective": objective, "nature": nature}
        ).eq("id", self.participant_id).execute()

    @classmethod
    def create(cls, room_code: str, create_participant: CreateParticipant):
        """
        Creates a new participant in a room.
        """
        res = (
            cls.get_table()
            .insert(
                {
                    **create_participant.model_dump(),
                    "room_code": room_code,
                }
            )
            .execute()
        )

        return cls(**res.data[0])

    @classmethod
    def create_multi(
        cls,
        participants: list[str],
        room_code: str,
        objective: str | None,
        nature: str | None,
        truth: str | None,
    ) -> Sequence["Participant"]:
        """
        Creates multiple participants in a room.
        """
        participants_data: list[dict] = []

        for email in participants:
            participants_data.append(
                {
                    "room_code": room_code,
                    "email": email,
                    "is_observer": False,
                    "objective": None,
                    "nature": None,
                    "truth": None,
                }
            )

        res = cls.get_table().insert(participants_data).execute()
        created_participants = [cls(**p) for p in res.data]

        # Set perspective only for AI Bot
        for participant in created_participants:
            if (
                participant.email == config.AIPARTICIPANT.AI_PARTICIPANT_EMAIL
                and truth
                and objective
                and nature
            ):
                participant.set_perspective(
                    truth=truth, objective=objective, nature=nature
                )
                break  # assuming only one AI participant

        return created_participants

    @classmethod
    def create_observers(
        cls, observers: list[str], room_code: str
    ) -> Sequence["Participant"]:
        """
        Creates observers in a room.
        """
        data: list[dict] = []

        for observer in observers:
            data.append(
                {
                    "room_code": room_code,
                    "email": observer,
                    "is_observer": True,
                }
            )

        if len(data) == 0:
            return []

        res = cls.get_table().insert(data).execute()
        return [cls(**o) for o in res.data]

    @classmethod
    def remove(cls, room_code: str, email: str) -> None:
        """
        Removes a participant from a room.
        """
        cls.get_table().delete().eq("room_code", room_code).eq("email", email).execute()

    @classmethod
    def fetch_by_room_code_and_email(cls, room_code: str, email: str):
        """
        Fetches a participant by room_code and email.
        """
        res = (
            cls.get_table()
            .select("*")
            .eq("room_code", room_code)
            .eq("email", email)
            .execute()
        )

        return cls(**res.data[0])

    @classmethod
    def fetch_room_codes_by_email(cls, email: str) -> list[str]:
        """
        Fetches all room codes for a participant by email.
        """
        res = cls.get_table().select("room_code").eq("email", email).execute()

        if not res.data:
            return []

        return [d["room_code"] for d in res.data]


@model(table_name="rooms")
class Room(BaseModel, BaseSupabaseModel):
    """
    This model corresponds to the "rooms" table in the database.
    Each row/instance in the table represents a room.
    The model provides methods to fetch, update and set the status of a room.
    """

    room_id: UUID = Field(alias="id")
    room_code: str
    room_name: str
    creator_email: EmailStr
    status: Optional[RoomStatus] = RoomStatus.MEDIATION
    created_at: AwareDatetime
    updated_at: Optional[PastDatetime]
    mediator_type: MediatorType
    parent_room_code: Optional[str]
    description: str
    completed_iterations: int = 0

    @classmethod
    def fetch_by_room_code(cls, room_code: str):
        """
        Fetches a room instance by room_code
        """
        room = cls._fetch_single_by_key_value("room_code", room_code)
        return room

    def get_conversation(self):
        """
        Fetches all the messages sent within a room
        """
        conversation = Conversation.from_room(self.room_code)
        return conversation

    def get_conversation_and_sub_rooms(self):
        """
        Fetches all the messages sent within a room and its sub-rooms.
        Used for final documentation, and not in the actual mediation process.
        """
        conversation = Conversation.from_rooms_and_sub_rooms(self.room_code)
        return conversation

    @property
    def is_public(self):
        """
        Returns True if the room is public, False otherwise.
        Was meant to be used for a public/private room feature.
        Currently used only to initiate a caucus - can be replaced with a suitable method.
        """
        return self.parent_room_code is None

    def get_parent_room(self):
        """
        Gets the parent room of a breakout room. Returns None if the room is a parent room.
        """
        if self.parent_room_code is None:
            return None
        return self.__class__.fetch_by_room_code(self.parent_room_code)

    def get_breakout_rooms(self):
        """
        Gets all breakout rooms of a parent room. Inverse of get_parent_room.
        """
        return {
            room.creator_email: room
            for room in self.__class__._fetch_by_key_value(
                "parent_room_code", self.room_code
            )
        }

    def participants(self, include_observers=False):
        """
        Returns all participants in a room.

        Args:
            include_observers: bool - whether to include observers in the list of participants
        """
        if include_observers:
            return Participant.fetch_for_room(room=self)
        else:
            return [
                p for p in Participant.fetch_for_room(room=self) if not p.is_observer
            ]

    def update_status(self, status: RoomStatus):
        """
        Sets the global status of a room. Currently not used.
        """
        if status == self.status:
            return
        self.status = status
        self.get_table().update({"status": self.status}).eq(
            "room_code", self.room_code
        ).execute()

    def increment_iterations(self):
        """
        Increments the number of completed iterations in a room.
        """
        self.completed_iterations += 1
        self.get_table().update({"completed_iterations": self.completed_iterations}).eq(
            "room_code", self.room_code
        ).execute()

    def update_mediator_type(self, mediator_type: MediatorType):
        """
        Updates the mediator type of a room.
        """
        self.mediator_type = mediator_type
        self.get_table().update({"mediator_type": self.mediator_type}).eq(
            "room_code", self.room_code
        ).execute()

    def fetch_all_by_room_name(self, room_name: str):
        """
        Fetches a all room instances sharing the same room_name
        """
        return self._fetch_by_key_value("room_name", room_name)

    def create_breakout_rooms(self, participants: list[Participant]) -> list["Room"]:
        """
        Creates breakout rooms for a parent room.
        """
        breakout_rooms: list[Room] = []

        for participant in participants:
            res = (
                self.get_table()
                .insert(
                    {
                        "parent_room_code": self.room_code,
                        "room_name": f"{self.room_name} - {participant.email}",
                        "creator_email": participant.email,
                        "mediator_type": self.mediator_type,
                        "description": self.description,
                        "room_code": generate_room_code(),
                    }
                )
                .execute()
            )

            breakout_rooms.append(res.data[0])

        return breakout_rooms

    @classmethod
    def create(cls, create_room: CreateRoom):
        """
        Create table.
        """
        room_code: str = generate_room_code()
        response = (
            cls.get_table()
            .insert(
                {
                    "room_name": create_room.room_name,
                    "room_code": room_code,
                    "creator_email": create_room.creator_email,
                    "mediator_type": create_room.mediator_type,
                    "parent_room_code": create_room.parent_room_code,
                    "description": create_room.description,
                }
            )
            .execute()
        )

        room = cls(**response.data[0])

        participants = Participant.create_multi(
            participants=[*create_room.participants],
            room_code=room.room_code,
            objective=create_room.objective,
            truth=create_room.truth,
            nature=create_room.nature,
        )

        observers = Participant.create_observers(create_room.observers, room.room_code)

        breakout_rooms = room.create_breakout_rooms(list(participants))  # CHECK THIS

        return {
            "room": room,
            "participants": participants,
            "observers": observers,
            "breakout_rooms": breakout_rooms,
        }

    @classmethod
    def fetch_by_room_code_and_creator_email(cls, room_code: str, email: str):
        """
        Fetches a room by room_code and creator_email.
        """
        res = (
            cls.get_table()
            .select("*")
            .eq("room_code", room_code)
            .eq("creator_email", email)
            .execute()
        )

        if not len(res.data):
            raise NotFound(
                message="Room not found with given room code and creator email."
            )

        return cls(**res.data[0])

    @classmethod
    def fetch_rooms_for_profile(cls, email: str):
        """
        Fetches all rooms for a participant by email.
        """
        room_codes: list[str] = Participant.fetch_room_codes_by_email(email)
        rooms = (
            cls.get_table()
            .select("*")
            .in_("room_code", list(set(room_codes)))
            .execute()
        )

        if not rooms.data:
            return []

        return [cls(**room) for room in rooms.data]
