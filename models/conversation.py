from typing import List
from pydantic import BaseModel
from models.message import Message, Role
from openai import OpenAI
from app.common import config

openai_client = OpenAI(
    api_key=config.OPENAI.OPENAI_API_KEY,
)


class Conversation(BaseModel):
    messages: List[Message]

    @classmethod
    def from_messages(cls, messages: List[Message]):
        """
        Creates a new conversation from a list of messages.
        """
        return cls(messages=messages)

    @classmethod
    def from_room(cls, room_code: str):
        """
        Creates a new conversation from a room code.
        """
        messages = Message.fetch_for_room_code(room_code)
        return cls.from_messages(messages=messages)

    @classmethod
    def from_rooms_and_sub_rooms(cls, room_code: str):
        """
        Creates a new conversation from a room code and all its sub-rooms.
        """
        messages = Message.fetch_including_sub_rooms_for_room_code(room_code)
        return cls.from_messages(messages=messages)

    def existing_summary_and_unsummarised_messages(self):
        """
        Returns the latest system message and the unsummarized messages.
        """
        latest_system_message_idx = None
        for i in range(len(self.messages) - 1, -1, -1):
            message = self.messages[i]
            if message.role == "system":
                latest_system_message_idx = i
                break
        summary = (
            ""
            if latest_system_message_idx is None
            else self.messages[latest_system_message_idx].content
        )
        unsummarized_messages = (
            self.messages
            if latest_system_message_idx is None
            else self.messages[latest_system_message_idx + 1 :]
        )
        return (summary, Conversation(messages=unsummarized_messages))

    def _summarize_messages(
        self, messages: List[Message], prompt: str, max_token_count: int
    ):
        """
        Summarizes a list of messages.
        """
        messages_content = "\n".join(
            f"{message.sender}: {message.content}" for message in messages
        )
        response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": messages_content},
            ],
            max_tokens=max_token_count,
        )
        summary = response.choices[0].message.content or ""
        return summary, True

    def summarize(
        self,
        number_of_messages_to_summarise: int = 5,
        prompt: str = "Summarize the following messages:",
        max_token_count: int = 600,
    ):
        """
        Summarizes the latest messages.
        """
        _, unsum_conv = self.existing_summary_and_unsummarised_messages()
        messages_to_summarise = unsum_conv.messages[-number_of_messages_to_summarise:]
        return self._summarize_messages(messages_to_summarise, prompt, max_token_count)

    def retrieve_latest_mediator_suggestion(self):
        """
        Retrieves the latest mediator suggestion.
        """
        latest_mediator_suggestion = None
        for message in reversed(self.messages):
            if (
                message.role == Role.MEDIATOR
                and "/EOM/".lower() in message.content.lower()
            ):
                latest_mediator_suggestion = message
                break
        return (
            Conversation(messages=[latest_mediator_suggestion])
            if latest_mediator_suggestion is not None
            else None
        )

    def summarize_latest_mediator_suggestion(
        self,
        prompt: str = "Summarize the following messages:",
        max_token_count: int = 600,
    ):
        """
        Summarizes the latest mediator suggestion.
        """
        latest_mediator_suggestion = self.retrieve_latest_mediator_suggestion()
        if latest_mediator_suggestion is not None:
            return self._summarize_messages(
                latest_mediator_suggestion.messages, prompt, max_token_count
            )
        else:
            return "", False

    @classmethod
    def merge(cls, conversations: List["Conversation"]) -> "Conversation":
        """
        Merges a list of conversations into a single conversation.
        """
        messages = []
        for conversation in conversations:
            messages.extend(conversation.messages)
        return cls(messages=sorted(messages, key=lambda m: m.created_at))

    def without_system(self):
        """
        Returns a new conversation with all system messages removed.
        """
        return self.__class__(
            messages=[
                message for message in self.messages if message.role != Role.SYSTEM
            ]
        )

    def latest_system_message(self):
        """
        Returns the latest system message.
        """
        for message in reversed(self.messages):
            if message.role == Role.SYSTEM:
                return message
        return None
