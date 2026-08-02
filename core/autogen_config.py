from typing import Callable
from models import Profile, Participant


def _load_config_from_file(filename: str) -> str:
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def create_config_from_folder(folder_name: str) -> dict:
    """
    Creates a config with all the necessary settings for the mediation process.
    """
    _CONFIG_CAUCUS_SYSTEM_COLLECTION: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/caucus_system_collection.txt"
    ).format(
        username=participant.profile.username,
        display_name=participant.profile.display_name,
        description=participant.room.description,
    )

    _CONFIG_CACUCUS_SYSTEM_ADVISOR: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/caucus_system_advisor.txt"
    ).format(
        username=participant.profile.username,
        display_name=participant.profile.display_name,
        description=participant.room.description,
    )

    _CONFIG_HUMANS_DESCRIPTION: Callable[[Profile], str] = (
        lambda profile: f"This is {profile.display_name} (also known as {profile.email}), a party involved in the conflict. They will talk only to their advisor."
    )

    _CONFIG_HUMANS_SYSTEM: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/dummy_system.txt"
    ).format(
        display_name=participant.profile.display_name,
        description=participant.room.description,
        truth=participant.truth,
        objective=participant.objective,
        nature=participant.nature,
    )

    _CONFIG_ADVISOR_DESCRIPTION: Callable[[Profile], str] = (
        lambda profile: f"Advisor for {profile.display_name} (also known as {profile.username})."
    )

    _CONFIG_COLLECTOR_SYSTEM: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/collector_system.txt"
    ).format(
        username=participant.profile.username,
        description=participant.room.description,
        display_name=participant.profile.display_name,
    )

    _CONFIG_ADVISOR_SYSTEM: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/advisor_system.txt"
    ).format(
        username=participant.profile.username,
        display_name=participant.profile.display_name,
        description=participant.room.description,
    )

    _CONFIG_CAUCUS_TERMINATION_PHRASE = "/NEOC/"
    _CONFIG_CAUCUS_SATISFACTION_PHRASE = "/PEOC/"
    _CONFIG_RESOLUTION_PHRASE = "It seems we have arrived at a resolution"

    _CONFIG_CAUCUS_SUMMARY: Callable[
        [Profile], str
    ] = lambda profile: _load_config_from_file(
        f"agent_config/{folder_name}/caucus_summary.txt"
    ).format(
        username=profile.username,
        display_name=profile.display_name,
    )

    _CONFIG_CAUCUS_SUMMARY_SATISFIED: Callable[
        [Profile], str
    ] = lambda profile: _load_config_from_file(
        f"agent_config/{folder_name}/caucus_summary_satisfied.txt"
    ).format(
        username=profile.username,
        display_name=profile.display_name,
    )

    _CONFIG_CAUCUS_SUMMARY_NO_RESOLUTION: Callable[
        [Profile], str
    ] = lambda profile: _load_config_from_file(
        f"agent_config/{folder_name}/caucus_summary_no_resolution.txt"
    ).format(
        username=profile.username,
        display_name=profile.display_name,
    )

    _CONFIG_CAUCUS_RESUME = ""

    _CONFIG_MEDIATION_GROUP_SYSTEM = _load_config_from_file(
        f"agent_config/{folder_name}/mediation_group_system.txt"
    )

    _CONFIG_MEDIATION_GROUP_INITIAL_MESSAGE = """
    It seems that both the representatives have spoken to their respective clients and obtained more information.
    Mediator, begin by summarizing the information you already have, and then we can proceed to hear from the representatives.
    """

    _CONFIG_LAWYER_DESCRIPTION: Callable[[Profile], str] = (
        lambda profile: f"Representative for {profile.display_name} (also known as {profile.username})."
    )

    _CONFIG_LAWYER_SYSTEM: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/lawyer_system.txt"
    ).format(
        username=participant.profile.username,
        display_name=participant.profile.display_name,
        description=participant.room.description,
    )

    _CONFIG_MEDIATOR_SYSTEM: Callable[[str], str] = (
        lambda description: _load_config_from_file(
            f"agent_config/{folder_name}/mediator_system.txt"
        ).format(description=description)
    )

    _CONFIG_MEDIATION_SUMMARY_GENERAL = _load_config_from_file(
        f"agent_config/{folder_name}/mediation_summary_general.txt"
    )

    _CONFIG_MEDIATION_SUMMARY_INDIVIDUAL: Callable[
        [Participant], str
    ] = lambda participant: _load_config_from_file(
        f"agent_config/{folder_name}/mediation_summary_individual.txt"
    ).format(
        username=participant.profile.username,
        display_name=participant.profile.display_name,
    )

    _CONFIG_CHECKER_SYSTEM = _load_config_from_file(
        f"agent_config/{folder_name}/guardrails.txt"
    )

    _CONFIG_CHECKER_DESCRIPTION = (
        "Checker who checks Mediator's suggestions and provides feedback."
    )

    _CONFIG_MEDIATION_TERMINATION_PHRASE = "/EOC/"

    _CONFIG_MEDIATION_NO_RESOLUTION = "a mutual resolution is not possible."

    CONFIG = {
        "max_iterations": 3,
        "human": {
            "description": _CONFIG_HUMANS_DESCRIPTION,
            "system": _CONFIG_HUMANS_SYSTEM,
        },
        "advisors": {
            "collector_system": _CONFIG_COLLECTOR_SYSTEM,
            "advisor_system": _CONFIG_ADVISOR_SYSTEM,
            "description": _CONFIG_ADVISOR_DESCRIPTION,
        },
        "caucuses": {
            "collection": _CONFIG_CAUCUS_SYSTEM_COLLECTION,
            "advisor": _CONFIG_CACUCUS_SYSTEM_ADVISOR,
            "termination_phrase": _CONFIG_CAUCUS_TERMINATION_PHRASE,
            "satisfaction_phrase": _CONFIG_CAUCUS_SATISFACTION_PHRASE,
            "resume": _CONFIG_CAUCUS_RESUME,
        },
        "representatives": {
            "system": _CONFIG_LAWYER_SYSTEM,
            "description": _CONFIG_LAWYER_DESCRIPTION,
        },
        "mediator": {
            "system": _CONFIG_MEDIATOR_SYSTEM,
            "description": "Neutral Mediator in the Conflict Resolution. Provides suggestions to the representatives. Seeks to resolve the conflict.",
        },
        "checker": {
            "system": _CONFIG_CHECKER_SYSTEM,
            "description": _CONFIG_CHECKER_DESCRIPTION,
        },
        "mediation_group": {
            "system": _CONFIG_MEDIATION_GROUP_SYSTEM,
            "initial_message_prompt": _CONFIG_MEDIATION_GROUP_INITIAL_MESSAGE,
            "termination_phrase": _CONFIG_MEDIATION_TERMINATION_PHRASE,
            "resolution": _CONFIG_RESOLUTION_PHRASE,
            "no_resolution": _CONFIG_MEDIATION_NO_RESOLUTION,
            "mediation_check_interval": 2,
        },
        "summary": {
            "caucus": _CONFIG_CAUCUS_SUMMARY,
            "mediation_general": _CONFIG_MEDIATION_SUMMARY_GENERAL,
            "mediation_individual": _CONFIG_MEDIATION_SUMMARY_INDIVIDUAL,
            "caucus_satisfaction": _CONFIG_CAUCUS_SUMMARY_SATISFIED,
            "caucus_no_resolution": _CONFIG_CAUCUS_SUMMARY_NO_RESOLUTION,
        },
    }

    return CONFIG


CONFIG_HR = create_config_from_folder("hr_prod")
CONFIG_THERAPIST = create_config_from_folder("therapist_prod")
CONFIG_GENERAL = create_config_from_folder("general_prod")
CONFIG_PARENT = create_config_from_folder("parent_prod")
CONFIG_LEGAL = create_config_from_folder("legal_prod")
