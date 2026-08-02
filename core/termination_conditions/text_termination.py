from typing import Sequence
from typing_extensions import Self
from pydantic import BaseModel
from autogen_agentchat.base import TerminatedException, TerminationCondition
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, StopMessage
from autogen_core import Component


class CaseInsensitiveTextMentionTerminationConfig(BaseModel):
    """
    Config for the text-based termination condition.
    """

    text: str


class CaseInsensitiveTextMentionTermination(
    TerminationCondition, Component[CaseInsensitiveTextMentionTerminationConfig]
):
    """Terminate the conversation if a specific text is mentioned.


    Args:
        text: The text to look for in the messages.
        sources: Check only messages of the specified agents for the text to look for.
    """

    component_config_schema = CaseInsensitiveTextMentionTerminationConfig
    component_provider_override = "autogen_agentchat.conditions.TextMentionTermination"

    def __init__(self, text: str, sources: Sequence[str] | None = None) -> None:
        self._termination_text = text
        self._terminated = False
        self._sources = sources

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if self._sources is not None and message.source not in self._sources:
                continue

            content = message.to_text()
            if self._termination_text.lower() in content.lower():
                self._terminated = True
                return StopMessage(
                    content=f"Text '{self._termination_text}' mentioned",
                    source="TextMentionTermination",
                )
        return None

    async def reset(self) -> None:
        self._terminated = False

    def _to_config(self) -> CaseInsensitiveTextMentionTerminationConfig:
        return CaseInsensitiveTextMentionTerminationConfig(text=self._termination_text)

    @classmethod
    def _from_config(cls, config: CaseInsensitiveTextMentionTerminationConfig) -> Self:
        return cls(text=config.text)
