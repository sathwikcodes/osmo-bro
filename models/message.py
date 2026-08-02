import logging
from uuid import UUID
from enum import Enum
from typing import Type, TypedDict, Unpack, cast
from lib.exceptions import NotFound
from pydantic import BaseModel, Field, EmailStr, AwareDatetime
from models.base import BaseSupabaseModel
from lib.utils import model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from models.profile import Profile
from deprecated import deprecated

logger = logging.getLogger("Message")


class Role(str, Enum):
    """
    Enum to represent the role of the sender of a message.
    Corresponds to the "role" field in the "messages" table.
    """

    ASSISTANT = "assistant"
    ADVISOR = "advisor"
    REPRESENTATIVE = "representative"
    MANAGER = "manager"
    MEDIATOR = "mediator"
    USER = "user"
    SYSTEM = "system"
    RESOLUTION = "resolution"

    @deprecated(
        reason="Langchain migrated it's memory offerings to LangGraph, and this enum is no longer used."
    )
    def to_langchain(self) -> Type[BaseMessage]:
        """
        Converts the role to a Langchain message type.
        """
        return cast(
            Type[BaseMessage],
            {
                Role.ASSISTANT: AIMessage,
                Role.ADVISOR: AIMessage,
                Role.REPRESENTATIVE: AIMessage,
                Role.MEDIATOR: AIMessage,
                Role.MANAGER: AIMessage,
                Role.USER: HumanMessage,
                Role.SYSTEM: SystemMessage,
            }[self],
        )


class MessageInput(TypedDict):
    """
    TypedDict to represent and check the input to the send_message() method of the Message class.
    """

    email: str
    content: str
    sender: str
    room_code: str
    role: str
    has_image: bool
    image_url: str | None
    image_analysis: str | None


@model(table_name="messages")
class Message(BaseSupabaseModel, BaseModel):
    """
    The Messages model corresponds to the "messages" table in the database.
    Each row/instance in the table represents a message sent by a user in a room.
    The model provides methods to send a message, and to fetch all messages for a room.
    """

    message_id: UUID = Field(alias="id")
    email: EmailStr
    sender: str
    created_at: AwareDatetime
    content: str
    room_code: str
    role: Role
    has_image: bool = False
    image_url: str | None = None
    image_analysis: str | None = None

    @classmethod
    def send_message(cls, **message: Unpack[MessageInput]):
        """
        Sends a message to the database.
        """
        try:
            response = cls.get_table().insert(dict(message)).execute()
            return cls(**response.data[0])
        except Exception as e:
            logger.error("Error sending message: %s", e)
            raise

    @classmethod
    def fetch_for_room_code(cls, room_code: str):
        """
        Fetches all messages for a room.
        """
        return cls._fetch_by_key_value("room_code", room_code)

    @classmethod
    def fetch_including_sub_rooms_for_room_code(cls, room_code: str):
        """
        Fetches all messages for a room and its sub-rooms.
        """
        return cls._fetch_by_key_value_similar("room_code", room_code)

    @deprecated(
        reason="This method was used for summarization, which is now handled by the Conversation class using the messages table"
    )
    def with_prefix(self):
        username = Profile.fetch_by_email(self.email).display_name
        if self.role != Role.USER:
            username = str(self.role.value)
        if not username:
            return self
        prefix = f"[{username}]: "
        if self.content.startswith(prefix):
            return self
        modified = self.model_copy()
        modified.content = prefix + modified.content
        return modified

    @classmethod
    def fetch_most_recent_by_room_code(cls, room_code: str):
        res = (
            cls.get_table()
            .select("*")
            .eq("room_code", room_code)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise NotFound(message="No messages found for the room.")

        return cls(**res.data[0])

    @classmethod
    def fetch_last_message(cls, room_code: str, sender: str):
        """
        Fetches latest message from a particular sender in a particular room
        """
        return cls._fetch_last_single_by_mult_key_value(
            ["room_code", "sender"], [room_code, sender]
        )
