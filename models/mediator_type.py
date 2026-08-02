from enum import Enum


class MediatorType(str, Enum):
    """
    Enum to represent the type of mediator in a room.
    Can be used to have different settings for different
    types of mediators, like system prompts, etc.
    """

    THERAPIST = "therapist"
    HR = "hr"
    GENERAL = "general"
    PARENT = "parent"
    LEGAL = "legal"
