import re
import logging
from pydantic import BaseModel
from models import Room, MediatorType
from core.autogen_config import (
    CONFIG_GENERAL,
    CONFIG_HR,
    CONFIG_LEGAL,
    CONFIG_PARENT,
    CONFIG_THERAPIST,
)

logger = logging.getLogger("RoomManager")


class RoomManager(BaseModel):
    """
    Manages the mediation rooms and their configurations.
    This class provides methods to sanitize display names,
    and retrieve room configurations based on the mediator type.
    """

    @staticmethod
    def sanitize_display_name(display_name: str) -> str:
        """
        Ensures the display name is safely formatted for use in identifiers.
        Replaces spaces with underscores and removes special characters.
        """
        return re.sub(r"[^a-zA-Z0-9_]", "", display_name.replace(" ", "_"))

    @staticmethod
    def get_room_config(room: Room):
        """
        Get the room configuration based on the room type
        """
        if room.mediator_type == MediatorType.HR:
            logger.info("HR Configuration Set.")
            return CONFIG_HR
        elif room.mediator_type == MediatorType.THERAPIST:
            logger.info("Therapist Configuration Set.")
            return CONFIG_THERAPIST
        elif room.mediator_type == MediatorType.PARENT:
            logger.info("Parent Configuration Set.")
            return CONFIG_PARENT
        elif room.mediator_type == MediatorType.LEGAL:
            logger.info("Legal Configuration Set.")
            return CONFIG_LEGAL
        else:
            logger.info("General Configuration Set.")
            return CONFIG_GENERAL
