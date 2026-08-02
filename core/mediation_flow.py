import logging
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from models.message import Message, Role
from models.profile import Profile
from models.room import Participant, Room, RoomStatus, Status
from core.agent_setup import RoomAgents, AgentSetup
from core.room_manager import RoomManager
from core.model_setup import OpenAIModelSetup
from core.outgoing_message import HandleOutgoingMessage

logger = logging.getLogger("MediationFlow")
model_setup = OpenAIModelSetup()


class FirstQuestionSchema(BaseModel):
    greeting: str
    context: str
    question: str


class MediationFlow(BaseModel):
    """
    Core class for managing the mediation process between Autogen AI agents and human participants.
    This class orchestrates the flow of mediation, including caucus initialization, mediation, and post-mediation checks.
    It handles the communication between participants, agents, and the mediation system.
    """

    @classmethod
    async def mediate(cls, room: Room):
        room = room.get_parent_room() or room
        participants = room.participants()

        status_counts = {
            Status.INIT: 0,
            Status.IN_CAUCUS: 0,
            Status.IN_MEDIATION: 0,
            Status.MEDIATION_DONE: 0,
            Status.SATISFIED: 0,
            Status.AWAITING_MEDIATION: 0,
            Status.RESOLVED: 0,
            Status.NO_RESOLUTION: 0,
        }

        for participant in participants:
            status_counts[participant.status] += 1

        logger.info("Participant Status Breakdown: %s", status_counts)

        CONFIG = RoomManager.get_room_config(room)

        if all(
            [participant.status == Status.SATISFIED for participant in participants]
        ):
            for participant in participants:
                participant.update_status(Status.RESOLVED)

            breakout_rooms = room.get_breakout_rooms()
            for email, breakout_room in breakout_rooms.items():
                conversation = breakout_room.get_conversation()
                profile = Profile.fetch_by_email(email)

                if conversation is None:
                    summary = "No previous conversation available."
                else:
                    summary, _ = conversation.summarize(
                        prompt=CONFIG["summary"]["caucus_satisfaction"](profile)
                    )

                breakout_room.update_status(RoomStatus.RESOLVED)

                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.SYSTEM,
                    content=(
                        f"The conflict is resolved.{profile.display_name} is satisfied with the resolution. Here is a summary of the accepted resolution: \n\n{summary}"
                    ),
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )
                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.RESOLUTION,
                    content=summary,
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

            room.update_status(RoomStatus.RESOLVED)

            logger.info(
                "All participants are satisfied. The mediation process is complete."
            )
            return

        elif not all(
            [
                participant.status == Status.AWAITING_MEDIATION
                or participant.status == Status.SATISFIED
                for participant in participants
            ]
        ):
            logger.info(
                "Some participants are still talking to their representatives. Please wait for all participants to finish talking."
            )
            return

        agents = await AgentSetup.create_agents(room=room)
        CONFIG = RoomManager.get_room_config(room)

        conversation = room.get_conversation()

        mediation_summary = room.description

        if conversation is not None:
            latest_system_message = conversation.latest_system_message()
            if latest_system_message is not None:
                mediation_summary = latest_system_message.content

        initial_message = f"Hello, I hope you have had a productive conversation with your clients. Here is my latest knowledge of the situation:\n\n{mediation_summary}\n\nRepresenatives, please provide your respective party's perspectives and additional insights you may have obtained."

        for participant in participants:
            participant.update_status(Status.IN_MEDIATION)

        breakout_rooms = room.get_breakout_rooms()

        for email, breakout_room in breakout_rooms.items():
            conversation = breakout_room.get_conversation()
            profile = Profile.fetch_by_email(email)

            if conversation is None:
                summary = "No previous conversation available."
            else:
                summary, _ = conversation.summarize(
                    prompt=CONFIG["summary"]["caucus"](profile)
                )

            existing_agent_system_message = (
                agents["representatives"][email]._system_messages[0].content
            )
            new_agent_system_message = f"{existing_agent_system_message}\n\n{summary}"
            agents["representatives"][email]._system_messages[
                0
            ].content = new_agent_system_message

            Message.send_message(
                room_code=breakout_room.room_code,
                sender="system",
                email=email,
                role=Role.SYSTEM,
                content=(f"{profile.display_name}'s perspective: \n\n{summary}"),
                has_image=False,
                image_url=None,
                image_analysis=None,
            )

        await HandleOutgoingMessage.send_message(
            room=room,
            sender=agents["mediator"],
            recipient=agents["mediation_team"],
            content=initial_message,
            agents=agents,
        )

        for participant in participants:
            participant.update_status(Status.MEDIATION_DONE)

        await cls.post_mediation_check(room=room, agents=agents)

    @classmethod
    async def post_mediation_check(cls, agents: RoomAgents, room: Room):
        """
        Checks for a case of no resolution and updates the status of the participants accordingly.
        No resolution is reached if:
        - the mediator determines that the conflict cannot be resolved.
        - maximum number of iterations is reached.
        """
        CONFIG = RoomManager.get_room_config(room)

        room.increment_iterations()
        for breakout_room in room.get_breakout_rooms().values():
            breakout_room.increment_iterations()

        if room.completed_iterations > CONFIG["max_iterations"]:

            for participant in room.participants():
                participant.update_status(Status.NO_RESOLUTION)

            room.update_status(RoomStatus.NO_RESOLUTION)
            logger.info(
                "Maximum number of iterations (%s) reached. The mediation process is complete. No resolution was reached.",
                CONFIG["max_iterations"],
            )

            breakout_rooms = room.get_breakout_rooms()
            for email, breakout_room in breakout_rooms.items():

                conversation = breakout_room.get_conversation()
                profile = Profile.fetch_by_email(email)

                if conversation is None:
                    summary = "No previous conversation available."
                else:
                    summary, _ = conversation.summarize(
                        prompt=CONFIG["summary"]["caucus_no_resolution"](profile)
                    )

                breakout_room.update_status(RoomStatus.NO_RESOLUTION)

                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.SYSTEM,
                    content=(
                        f"The conflict is unresolved. Maximum mediation iterations ({room.completed_iterations}) reached.\n\n"
                        f"**Resolution provided to {profile.display_name}:**\n{summary}"
                    ),
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.RESOLUTION,
                    content=(
                        f"The conflict is unresolved. Maximum mediation iterations ({room.completed_iterations}) reached.\n\n"
                        f"**Resolution provided to {profile.display_name}:**\n{summary}"
                    ),
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

            return

        elif (
            room.completed_iterations
            % CONFIG["mediation_group"]["mediation_check_interval"]
            == 0
        ):

            agents["mediator"]._system_messages[0].content = CONFIG["mediator"][
                "system"
            ](room.description)

            for participant in room.participants():

                agents["advisors"][participant.email]._system_messages[0].content = (
                    CONFIG["advisors"]["advisor_system"](participant)
                )

                agents["representatives"][participant.email]._system_messages[
                    0
                ].content = CONFIG["representatives"]["system"](participant)

        last_message = Message.fetch_last_message(room.room_code, "Mediator")
        participants = room.participants()
        if (
            last_message
            and CONFIG["mediation_group"]["no_resolution"].lower()
            in last_message.content.lower()
        ):

            Message.send_message(
                room_code=room.room_code,
                sender="system",
                email=room.creator_email,
                role=Role.SYSTEM,
                content=(
                    "The conflict is unresolved. The mediator has determined that the conflict cannot be resolved."
                ),
                has_image=False,
                image_url=None,
                image_analysis=None,
            )

            for participant in participants:
                if participant.status == Status.MEDIATION_DONE:
                    participant.update_status(Status.NO_RESOLUTION)

            breakout_rooms = room.get_breakout_rooms()
            for email, breakout_room in breakout_rooms.items():
                breakout_room.update_status(RoomStatus.NO_RESOLUTION)

                conversation = breakout_room.get_conversation()
                profile = Profile.fetch_by_email(email)

                if conversation is None:
                    summary = "No previous conversation available."
                else:
                    summary, _ = conversation.summarize(
                        prompt=CONFIG["summary"]["caucus_no_resolution"](profile)
                    )

                breakout_room.update_status(RoomStatus.NO_RESOLUTION)
                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.RESOLUTION,
                    content=(
                        f"The conflict is unresolved. Maximum mediation iterations ({room.completed_iterations}) reached.\n\n"
                        f"**Resolution provided to {profile.display_name}:**\n{summary}"
                    ),
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=email,
                    role=Role.SYSTEM,
                    content=(
                        f"The conflict is unresolved. Maximum mediation iterations ({room.completed_iterations}) reached.\n\n"
                        f"**Resolution provided to {profile.display_name}:**\n{summary}"
                    ),
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

            room.update_status(RoomStatus.NO_RESOLUTION)
            logger.info("No resolution was reached. The mediation process is complete.")
            return

        await cls.resume_caucus(room=room, agents=agents)

    @classmethod
    async def post_caucus(cls, agents: RoomAgents, room: Room):
        name = agents["advisors"][room.creator_email].name
        formatted_name = name.replace("_advisor", "").title() + "'s Advisor"
        last_message = Message.fetch_last_message(room.room_code, formatted_name)

        participant = Participant.fetch_for_room_email(
            room=room, email=room.creator_email
        )
        CONFIG = RoomManager.get_room_config(room)
        if (
            last_message
            and CONFIG["caucuses"]["satisfaction_phrase"].lower()
            in last_message.content.lower()
        ):
            participant.update_status(Status.SATISFIED)
        elif (
            last_message
            and CONFIG["caucuses"]["termination_phrase"].lower()
            in last_message.content.lower()
        ):
            participant.update_status(Status.AWAITING_MEDIATION)

        return await cls.mediate(room)

    @staticmethod
    async def call_for_first_question(
        description: str, all_participants: list[Participant], current_participant: str
    ) -> str:

        parties_str = " and ".join(
            [participant.profile.display_name for participant in all_participants]
        )
        prompt = f"""There is a conflict between the parties: {parties_str}. Your job is to ask questions to one of the parties to understand their context better.
        Based on the provided description of the conflict between them, what is logical next follow up question that should be asked to understand {current_participant}'s further context better?
        Make sure to be caring and empathetic in the way you ask the question.
        The language you use has to be the same as that of the description I provided only.
        Here is the description: {description}
        Just give me your entire response as one paragraph:
        'Hello and welcome to ResolvewithAI! I'll be your representative throughout this conflict mediation process, ensuring that your concerns are heard and addressed. My role is to gather relevant information, guide you through the process, and provide helpful insights to support a fair resolution.' (change this line into the langauge as description if not in english)

        '**Here is what I know so far about your case**' (followed by the EXACT description given above copy pasted on a new line so change this line into the langauge as description if not in english)
        '**To get started, let's focus on the following:**' (followed by the question you need to come up with based on the context on a new line, again match this entire line w question to the languae of description if not already english. Address {current_participant} cirectly in the question you add.)
        """

        response = await model_setup.openai_chat_client.agenerate(
            [[HumanMessage(content=prompt)]]
        )
        return str(response.generations[0][0].text)

    @classmethod
    async def initialise_caucus(cls, room: Room):
        if room.is_public:
            raise ValueError(
                "This room is not a caucus. Please provide a caucus to initialise"
            )
        parent = room.get_parent_room()
        if not parent:
            raise ValueError("No parent room found for caucus!")
        all_participants = Participant.fetch_for_room(room=parent)

        participant = Participant.fetch_for_room_email(
            room=room, email=room.creator_email
        )
        if participant.status != Status.INIT:
            raise Exception(
                f"Participant {participant.profile.display_name} ({participant.room_code}) not in the {Status.INIT} state."
            )
        agents = await AgentSetup.create_agents(room=parent)
        participant.update_status(Status.IN_CAUCUS)

        first_question = await cls.call_for_first_question(
            room.description, all_participants, participant.profile.display_name
        )

        await HandleOutgoingMessage.send_message(
            room=room,
            sender=agents["advisors"][room.creator_email],
            recipient=agents["caucuses"][room.creator_email],
            content=first_question,
            agents=agents,
        )
        await cls.post_caucus(agents=agents, room=room)

    @classmethod
    async def resume_caucus(cls, room: Room, agents: RoomAgents):
        room = room.get_parent_room() or room

        if room.status != RoomStatus.MEDIATION:
            return

        breakout_rooms = room.get_breakout_rooms()
        conversation = room.get_conversation()
        CONFIG = RoomManager.get_room_config(room)
        if conversation is None:
            summary = "No previous conversation available."
        else:
            summary = conversation.summarize(
                prompt=CONFIG["summary"]["mediation_general"]
            )[0]

            existing_mediator_system_message = (
                agents["mediator"]._system_messages[0].content
            )
            new_mediator_system_message = (
                f"{existing_mediator_system_message}\n\n{summary}"
            )
            agents["mediator"]._system_messages[0].content = new_mediator_system_message

        Message.send_message(
            room_code=room.room_code,
            sender="system",
            email=room.creator_email,
            role=Role.SYSTEM,
            content=summary,
            has_image=False,
            image_url=None,
            image_analysis=None,
        )

        for email, breakout_room in breakout_rooms.items():
            if conversation is None:
                room_summary = ""
            else:
                participant = Participant.fetch_for_room_email(room=room, email=email)
                room_summary = conversation.summarize_latest_mediator_suggestion(
                    prompt=CONFIG["summary"]["mediation_individual"](participant)
                )[0]

                Message.send_message(
                    room_code=breakout_room.room_code,
                    sender="system",
                    email=room.creator_email,
                    role=Role.SYSTEM,
                    content=room_summary,
                    has_image=False,
                    image_url=None,
                    image_analysis=None,
                )

                existing_advisor_system_message = (
                    agents["advisors"][email]._system_messages[0].content
                )

                if (
                    CONFIG["advisors"]["collector_system"](participant)
                    in existing_advisor_system_message
                ):
                    agents["advisors"][email]._system_messages[0].content = (
                        CONFIG["advisors"]["advisor_system"](participant)
                        + f"\n\n{room_summary}"
                    )

                else:
                    agents["advisors"][email]._system_messages[0].content = (
                        existing_advisor_system_message + f"\n\n{room_summary}"
                    )
            participant.update_status(Status.IN_CAUCUS)
            await HandleOutgoingMessage.send_message(
                room=breakout_room,
                sender=agents["advisors"][email],
                recipient=agents["caucuses"][email],
                content=(CONFIG["caucuses"]["resume"] + f"\n\n{room_summary}"),
                agents=agents,
                has_image=False,
                image_url=None,
                image_analysis=None,
            )

            await cls.post_caucus(agents=agents, room=breakout_room)
