import logging
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import SelectorGroupChat
from models import Message, Role, Profile, Room
from core.room_manager import RoomManager
from core.agent_setup import RoomAgents

logger = logging.getLogger("OutgoingMessage")


class HandleOutgoingMessage(BaseModel):
    """
    Handles outgoing messages in the mediation process.
    This class is responsible for sending messages from agents to the appropriate recipients,
    ensuring that the conversation flow is maintained and that messages are correctly formatted.
    """

    @staticmethod
    def __get_role_from_agent_name(agent_name: str) -> Role:
        if agent_name == "mediator":
            return Role.MEDIATOR
        if "representative" in agent_name.lower():
            return Role.REPRESENTATIVE
        if "advisor" in agent_name.lower():
            return Role.ADVISOR
        if (
            "caucus" in agent_name.lower()
            or agent_name.endswith("mediation")
            or agent_name.endswith("mediator")
        ):
            return Role.MANAGER
        return Role.USER

    @staticmethod
    def __get_agent_by_name(room_agents: RoomAgents, name: str):
        agents: dict[str, UserProxyAgent | AssistantAgent] = {
            agent.name: agent
            for agent in [
                room_agents["mediator"],
                *room_agents["humans"].values(),
                *room_agents["representatives"].values(),
                *room_agents["advisors"].values(),
                room_agents["checker"],
            ]
        }
        return agents[name]

    @staticmethod
    def __get_email_from_agent(agent: UserProxyAgent | AssistantAgent):
        metadata = getattr(agent, "metadata", {})
        profile: Profile | None = metadata.get("profile")
        email = profile.email if profile else None
        return email

    @staticmethod
    def __get_display_name_from_agent(agent: UserProxyAgent | AssistantAgent) -> str:
        """
        Get the display name for an agent based on its metadata or name.
        For human agents and representatives, use the profile's display_name.
        For other agents (mediator, checker), use their default names.
        """
        metadata = getattr(agent, "metadata", {})
        profile: Profile | None = metadata.get("profile")

        if profile:
            sanitized_display_name = RoomManager.sanitize_display_name(
                profile.display_name
            )
            if agent.name.endswith("_representative"):
                return sanitized_display_name + "'s Representative"
            elif agent.name.endswith("_advisor"):
                return sanitized_display_name + "'s Advisor"
            else:
                return sanitized_display_name
        elif agent.name == "mediator":
            return "Mediator"
        elif agent.name == "checker":
            return "Checker"
        else:
            return agent.name

    @classmethod
    async def send_message(
        cls,
        room: Room,
        sender: UserProxyAgent | AssistantAgent,
        recipient: SelectorGroupChat,
        content: str,
        agents: RoomAgents,
        ignore_initial_message=False,
        has_image: bool = False,
        image_url: str | None = None,
        image_analysis: str | None = None,
    ):
        room_to_send = room.get_parent_room() or room
        email = cls.__get_email_from_agent(sender) or room.creator_email

        if sender.name != "mediator" and not sender.name.endswith("_representative"):
            if not room.is_public:
                room_to_send = room
            else:
                breakouts = room_to_send.get_breakout_rooms()
                if email in breakouts:
                    room_to_send = breakouts[email]

        message_content = content
        if has_image and image_analysis:
            message_content = f"{content}\n\nImage Analysis:\n{image_analysis}"

        if not ignore_initial_message:
            sender_display_name = cls.__get_display_name_from_agent(sender)

            Message.send_message(
                room_code=room_to_send.room_code,
                sender=sender_display_name,
                email=email,
                role=cls.__get_role_from_agent_name(sender.name),
                content=content,
                has_image=(
                    has_image
                    if cls.__get_role_from_agent_name(sender.name) == Role.USER
                    else False
                ),
                image_url=(
                    image_url
                    if cls.__get_role_from_agent_name(sender.name) == Role.USER
                    else None
                ),
                image_analysis=(
                    image_analysis
                    if cls.__get_role_from_agent_name(sender.name) == Role.USER
                    else None
                ),
            )

        message = TextMessage(content=message_content, source=sender.name)
        try:
            response = recipient.run_stream(task=[message])
            first = True
            async for inner_message in response:
                if isinstance(inner_message, BaseChatMessage):
                    print(f"**{inner_message.source}**\n{inner_message.to_text()}\n")
                    if first:
                        first = False
                        continue
                    if not isinstance(inner_message, TaskResult):

                        agent = cls.__get_agent_by_name(
                            room_agents=agents, name=inner_message.source
                        )
                        agent_display_name = cls.__get_display_name_from_agent(agent)

                        Message.send_message(
                            room_code=room_to_send.room_code,
                            sender=agent_display_name,
                            email=cls.__get_email_from_agent(agent)
                            or room.creator_email,
                            role=cls.__get_role_from_agent_name(inner_message.source),
                            content=inner_message.to_text(),
                            has_image=False,
                            image_url=None,
                            image_analysis=None,
                        )
        except Exception as e:
            logger.error("Error in send_message: %s", e)
        return Message.fetch_most_recent_by_room_code(room_to_send.room_code)
