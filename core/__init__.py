"""
Core components for managing the mediation process between Autogen AI agents and human participants.

This package contains classes that handle different aspects of the mediation process:
- Agent setup and configuration
- Message handling (incoming and outgoing)
- Mediation flow orchestration
- Room state management components
"""

import logging
from core.agent_setup import AgentSetup, RoomAgents
from core.incoming_message import HandleIncomingMessage
from core.outgoing_message import HandleOutgoingMessage
from core.mediation_flow import MediationFlow
from core.room_manager import RoomManager
from core.model_setup import OpenAIModelSetup

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AutogenAgent")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("autogen_core").setLevel(logging.WARNING)

__all__ = [
    "AgentSetup",
    "RoomAgents",
    "HandleIncomingMessage",
    "HandleOutgoingMessage",
    "MediationFlow",
    "RoomManager",
    "OpenAIModelSetup",
]
