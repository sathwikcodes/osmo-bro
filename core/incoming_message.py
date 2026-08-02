import asyncio
import logging
from pydantic import BaseModel
from app.common import config
from models.profile import Profile
from models.room import Room, Status
from lib.exceptions import BadRequest, NotFound
from lib.schema.message import CreateMessage
from core.agent_setup import AgentSetup
from core.room_manager import RoomManager
from core.mediation_flow import MediationFlow
from core.outgoing_message import HandleOutgoingMessage

AI_PARTICIPANT = config.AIPARTICIPANT.AI_PARTICIPANT_DISPLAY_NAME


class HandleIncomingMessage(BaseModel):
    """
    Handles incoming messages in the mediation process.
    This class is responsible for processing new messages from users,
    ensuring they are routed correctly, and managing the conversation flow.
    """

    @classmethod
    async def handle_new_message(
        cls, profile: Profile, room: Room, create_message: CreateMessage
    ):
        if room.is_public:
            raise BadRequest(
                message="All user messages should be initiated from a caucus. The provided room is public.",
            )

        if not profile:
            raise NotFound(message="Profile not found for current user.")

        parent = room.get_parent_room() or room
        agents = await AgentSetup.create_agents(room=parent)
        message = await HandleOutgoingMessage.send_message(
            room=parent,
            sender=agents["humans"][profile.email],
            recipient=agents["caucuses"][profile.email],
            content=create_message.content,
            agents=agents,
            has_image=create_message.has_image,
            image_url=create_message.image_url,
            image_analysis=create_message.image_analysis,
        )
        await MediationFlow.post_caucus(agents=agents, room=room)

        return message

    @classmethod
    async def initialize_ai_bot_conversation(cls, room: Room):
        """
        Initialize the AI bot's conversation in a breakout room.
        This should be called when initializing the main room.
        """
        parent_room = room.get_parent_room() or room
        breakout_rooms = parent_room.get_breakout_rooms()

        ai_participant = None
        for participant in parent_room.participants():
            if RoomManager.sanitize_display_name(
                participant.profile.display_name
            ) == RoomManager.sanitize_display_name(AI_PARTICIPANT):
                ai_participant = participant
                break

        if not ai_participant:
            logging.info("No AI bot participant found in the room")
            return

        ai_room = breakout_rooms[ai_participant.email]
        agents = await AgentSetup.create_agents(room=parent_room)
        logging.info("Starting AI bot conversation in room: %s", ai_room.room_code)

        async def run_ai_conversation():
            try:
                ai_participant.update_status(Status.IN_CAUCUS)

                first_question = await MediationFlow.call_for_first_question(
                    ai_room.description,
                    parent_room.participants(),
                    ai_participant.profile.display_name,
                )

                await HandleOutgoingMessage.send_message(
                    room=ai_room,
                    sender=agents["advisors"][ai_participant.email],
                    recipient=agents["caucuses"][ai_participant.email],
                    content=first_question,
                    agents=agents,
                )

            except Exception as e:
                logging.error("Error in AI bot conversation: %s", e)
            return await MediationFlow.post_caucus(agents=agents, room=room)

        asyncio.create_task(run_ai_conversation())
