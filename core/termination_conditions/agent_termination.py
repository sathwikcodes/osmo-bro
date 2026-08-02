from typing import Sequence
from typing_extensions import Self
from pydantic import BaseModel
from autogen_agentchat.base import TerminatedException, TerminationCondition
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, StopMessage
from autogen_core import Component


class AgentHandoffTerminationConfig(BaseModel):
    """
    Config for the agent handoff termination condition.
    """

    source_name: str


class AgentHandoffTermination(
    TerminationCondition, Component[AgentHandoffTerminationConfig]
):
    """Terminate the conversation if a specific agent is done talking."""

    component_config_schema = AgentHandoffTerminationConfig

    def __init__(self, source: str) -> None:
        self._terminated = False
        self._source = source

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        if messages[-1].source == self._source:
            self._terminated = True
            return StopMessage(
                content=f"Text '{self._source}' gave their message",
                source="AgentHandoffTermination",
            )
        return None

    async def reset(self) -> None:
        self._terminated = False

    def _to_config(self) -> AgentHandoffTerminationConfig:
        return AgentHandoffTerminationConfig(source_name=self._source)

    @classmethod
    def _from_config(cls, config: AgentHandoffTerminationConfig) -> Self:
        return cls(source=config.source_name)
