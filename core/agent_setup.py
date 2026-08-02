import logging
from typing import Dict, Sequence
from typing_extensions import TypedDict
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.teams import SelectorGroupChat
from models import Room, Participant
from core.model_setup import OpenAIModelSetup
from core.room_manager import RoomManager
from core.termination_conditions import (
    AgentHandoffTermination,
    CaseInsensitiveTextMentionTermination,
)
from app.common import config


class RoomAgents(TypedDict):
    """
    TypedDict to hold all agents and groups for a specific room.
    This includes:
    - humans: Dict of UserProxyAgent or AssistantAgent instances representing human participants.
    - advisors: Dict of AssistantAgent instances acting as advisors for each participant.
    - caucuses: Dict of SelectorGroupChat instances for each participant's caucus.
    - representatives: Dict of AssistantAgent instances acting as representatives for each participant.
    - mediator: An AssistantAgent instance acting as the mediator for the room.
    - checker: An AssistantAgent instance acting as the checker for the room.
    - mediation_team: A SelectorGroupChat instance managing the mediation process.
    """

    humans: Dict[str, UserProxyAgent | AssistantAgent]
    advisors: Dict[str, AssistantAgent]
    caucuses: Dict[str, SelectorGroupChat]
    representatives: Dict[str, AssistantAgent]
    mediator: AssistantAgent
    checker: AssistantAgent
    mediation_team: SelectorGroupChat


AI_PARTICIPANT = config.AIPARTICIPANT.AI_PARTICIPANT_DISPLAY_NAME
agent_cache: Dict[str, RoomAgents] = {}
model_setup = OpenAIModelSetup()
dummy_llm_config, agents_llm_config, representatives_llm_config, mediator_llm_config = (
    model_setup.get_all_configs()
)


class AgentSetup(BaseModel):
    """
    Responsible for creating and managing various agent roles and groups for a given Room.

    This class provides static and class methods to initialize:
    - Human agents (as UserProxyAgent or AssistantAgent instances),
    - Advisors and representatives (as AssistantAgent instances),
    - Mediator and checker agents (specialized AssistantAgents),
    - Caucus groups (SelectorGroupChat instances per participant),
    - The overall mediation team (SelectorGroupChat managing mediator, checker, and representatives).

    Agents are created based on room participants and configurations retrieved from RoomManager.
    The class handles special cases such as AI participants, ensures metadata attachment to agents,
    and supports conversation termination logic with custom termination conditions.

    All async methods are designed to be used within an asynchronous event loop,
    enabling integration with LLM model clients and asynchronous chat/message handling.

    Agent instances and groups are cached per room to avoid redundant initialization.

    Typical usage:
        agents = await AgentSetup.create_agents(room)
        humans = agents['humans']
        caucuses = agents['caucuses']
        mediation_team = agents['mediation_team']
    """

    @staticmethod
    async def _create_human_agents(room: Room):
        """
        Create UserProxyAgent instances for the participants in the room - can be LLM models when testing is True, else human agents
        """
        try:
            CONFIG = RoomManager.get_room_config(room)
            room = room.get_parent_room() or room
            participants = room.participants()
            humans: Dict[str, UserProxyAgent | AssistantAgent] = {}

            for participant in participants:

                key = str(participant.email)
                participant_profile = participant.profile
                sanitized_name = RoomManager.sanitize_display_name(
                    participant_profile.display_name
                )

                if (
                    sanitized_name == RoomManager.sanitize_display_name(AI_PARTICIPANT)
                    and participant.truth
                ):
                    model_client = await model_setup.create_model_client(
                        dummy_llm_config
                    )
                    humans[key] = AssistantAgent(
                        name=sanitized_name,
                        description=CONFIG["human"]["description"](participant_profile),
                        model_client=model_client,
                        system_message=CONFIG["human"]["system"](participant),
                    )
                else:
                    humans[key] = UserProxyAgent(name=sanitized_name)
                setattr(humans[key], "metadata", {"profile": participant_profile})
            return humans

        except Exception as e:
            logging.error("Error in _create_advisors_representatives: %s", e)
            raise

    @staticmethod
    async def _create_advisors_representatives(room: Room):
        """
        Creates AssistantAgent instances to act as advisors and representatives for each participant in the room.
        """
        try:
            CONFIG = RoomManager.get_room_config(room)
            room = room.get_parent_room() or room
            participants = room.participants()
            if not participants:
                raise ValueError(f"No participants found in room: {room.room_code}")
            advisors: Dict[str, AssistantAgent] = {}
            representatives: Dict[str, AssistantAgent] = {}
            model_client = await model_setup.create_model_client(agents_llm_config)
            for participant in participants:
                if not participant.email or not participant.profile:
                    raise ValueError(f"Invalid participant data: {participant}")
                key = str(participant.email)
                participant_profile = participant.profile
                sanitized_name = RoomManager.sanitize_display_name(
                    participant_profile.display_name
                )

                advisors[key] = AssistantAgent(
                    f"{sanitized_name.lower()}_advisor",
                    description=CONFIG["advisors"]["description"](participant_profile),
                    model_client=model_client,
                    system_message=CONFIG["advisors"]["collector_system"](participant),
                )

                setattr(advisors[key], "metadata", {"profile": participant})

                representatives[key] = AssistantAgent(
                    f"{sanitized_name.lower()}_representative",
                    description=CONFIG["representatives"]["description"](
                        participant_profile
                    ),
                    model_client=model_client,
                    system_message=CONFIG["representatives"]["system"](participant),
                )

                setattr(representatives[key], "metadata", {"profile": participant})

            return advisors, representatives
        except Exception as e:
            logging.error("Error in __create_advisors_representatives: %s", e)
            raise

    @staticmethod
    async def __prepare_caucus_for_participant(
        room: Room,
        participant: Participant,
        humans: Dict[str, UserProxyAgent | AssistantAgent],
        advisors: Dict[str, AssistantAgent],
        breakouts: Dict[str, Room],
    ) -> SelectorGroupChat | None:
        """
        Prepare a SelectorGroupChat caucus for a single participant.
        Returns None if no caucus should be created (e.g. AI participant with messages).
        """
        CONFIG = RoomManager.get_room_config(room)
        key = str(participant.profile.email)
        sanitized_name = RoomManager.sanitize_display_name(
            participant.profile.display_name
        )
        breakout = breakouts[key]

        messages = [
            TextMessage(
                content=msg.content,
                source=(
                    f"{sanitized_name.lower()}_advisor"
                    if "Advisor" in msg.sender
                    else f"{sanitized_name.lower()}_representative"
                ),
            )
            for msg in breakout.get_conversation().messages
        ]

        termination1 = CaseInsensitiveTextMentionTermination(
            CONFIG["caucuses"]["termination_phrase"], advisors[key].name
        )
        termination2 = CaseInsensitiveTextMentionTermination(
            CONFIG["caucuses"]["satisfaction_phrase"], advisors[key].name
        )
        termination3 = AgentHandoffTermination(advisors[key].name)

        def make_checker_sequence(name: str):
            def checker_sequence(
                messages: Sequence[BaseAgentEvent | BaseChatMessage],
            ) -> str | None:
                if "_advisor" not in messages[-1].source:
                    return f"{name.lower()}_advisor"
                else:
                    return name

            return checker_sequence

        model_client = await model_setup.create_model_client(mediator_llm_config)
        selector_func = make_checker_sequence(sanitized_name)

        is_ai_participant = sanitized_name == RoomManager.sanitize_display_name(
            AI_PARTICIPANT
        )

        if is_ai_participant:
            if not messages:
                termination = termination1 | termination2
            else:
                return None  # skip caucus creation for AI participant with existing messages
        else:
            termination = termination1 | termination2 | termination3

        caucus = SelectorGroupChat(
            participants=[humans[key], advisors[key]],
            max_turns=35,
            model_client=model_client,
            selector_func=selector_func,
            termination_condition=termination,
        )

        if messages and not is_ai_participant:
            response = await caucus.run(task=messages)
            for msg in response.messages:
                print(msg.source, ":", msg.to_text())

        setattr(caucus, "metadata", {"profile": participant})

        return caucus

    @classmethod
    async def _create_caucuses(
        cls,
        room: Room,
        humans: Dict[str, UserProxyAgent | AssistantAgent],
        advisors: Dict[str, AssistantAgent],
    ) -> Dict[str, SelectorGroupChat]:
        """
        Create SelectorGroupChat caucuses for each participant in the room.
        """
        try:
            room = room.get_parent_room() or room
            participants = room.participants()
            if not participants:
                raise ValueError(f"No participants found in room: {room.room_code}")

            breakouts = room.get_breakout_rooms()
            caucuses: Dict[str, SelectorGroupChat] = {}

            for participant in participants:
                caucus = await cls.__prepare_caucus_for_participant(
                    room, participant, humans, advisors, breakouts
                )
                if caucus is not None:
                    key = str(participant.profile.email)
                    caucuses[key] = caucus

            return caucuses

        except Exception as e:
            logging.error("Error in _create_caucuses: %s", e)
            raise

    @staticmethod
    async def _create_mediator(room: Room):
        """
        Creates an AssistantAgent instance to act as the mediator for the room.
        """
        CONFIG = RoomManager.get_room_config(room)
        model_client = await model_setup.create_model_client(mediator_llm_config)

        mediator = AssistantAgent(
            "mediator",
            model_client=model_client,
            description=CONFIG["mediator"]["description"],
            system_message=CONFIG["mediator"]["system"](room.description),
        )
        return mediator

    @staticmethod
    async def _create_checker(room: Room):
        """
        Creates a UserProxy instance to act as the checker for the room.
        """
        CONFIG = RoomManager.get_room_config(room)
        model_client = await model_setup.create_model_client(mediator_llm_config)

        checker = AssistantAgent(
            "checker",
            model_client=model_client,
            description=CONFIG["checker"]["description"],
            system_message=CONFIG["checker"]["system"],
        )
        return checker

    @staticmethod
    async def _create_mediation_team(
        room: Room,
        mediator: AssistantAgent,
        representatives: Dict[str, AssistantAgent],
        checker: AssistantAgent,
    ):
        """
        Creates a SelectorGroupChat instance to manage the mediation process for the room.
        """
        CONFIG = RoomManager.get_room_config(room)

        def checker_sequence(
            messages: Sequence[BaseAgentEvent | BaseChatMessage],
        ) -> str | None:
            representatives_list = list(representatives.values())
            representatives_list_str = [
                representative.name for representative in representatives_list
            ]
            if messages[-1].source == mediator.name:
                if "/EOM/".lower() in messages[-1].to_text().lower():
                    return checker.name
                return representatives_list_str[0]
            elif messages[-1].source in representatives_list_str:
                i = representatives_list_str.index(messages[-1].source)
                if i < len(representatives_list) - 1:
                    return representatives_list_str[i + 1]
                return mediator.name
            elif messages[-1].source == checker.name:
                return mediator.name
            return mediator.name

        termination1 = CaseInsensitiveTextMentionTermination(
            CONFIG["mediation_group"]["termination_phrase"].lower(), mediator.name
        )
        termination2 = CaseInsensitiveTextMentionTermination(
            CONFIG["mediation_group"]["no_resolution"].lower(), mediator.name
        )
        combined_termination = termination1 | termination2
        model_client = await model_setup.create_model_client(mediator_llm_config)
        mediation_team = SelectorGroupChat(
            participants=[mediator, checker, *representatives.values()],
            max_turns=15,
            model_client=model_client,
            selector_func=checker_sequence,
            allow_repeated_speaker=False,
            selector_prompt=CONFIG["mediation_group"]["system"],
            termination_condition=combined_termination,
        )

        return mediation_team

    @classmethod
    async def create_agents(cls, room: Room):
        """
        Creates all agents and groups
        """
        room = room.get_parent_room() or room
        if room.room_code in agent_cache:
            return agent_cache[room.room_code]

        humans = await cls._create_human_agents(room)
        advisors, representatives = await cls._create_advisors_representatives(room)
        mediator = await cls._create_mediator(room)
        caucuses = await cls._create_caucuses(room, humans, advisors)
        checker = await cls._create_checker(room)
        mediation_team = await cls._create_mediation_team(
            room, mediator, representatives, checker
        )

        out = RoomAgents(
            humans=humans,
            advisors=advisors,
            representatives=representatives,
            caucuses=caucuses,
            mediator=mediator,
            checker=checker,
            mediation_team=mediation_team,
        )
        agent_cache[room.room_code] = out
        return out
