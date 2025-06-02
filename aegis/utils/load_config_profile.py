from pathlib import Path
import yaml
from aegis.agents.node_registry import AGENT_NODE_REGISTRY
from aegis.schemas.config import AgentConfig
from aegis.utils.logger import setup_logger
from aegis.utils.type_resolver import resolve_dotted_type

logger = setup_logger(__name__)


def validate_node_names(config: dict):
    """
    validate_node_names.
    :param config: Description of config
    :type config: Any
    :return: Description of return value
    :rtype: Any
    """
    keys = [config.get("entrypoint"), config.get("condition_node")]
    keys += [t for edge in config.get("edges", []) for t in edge]
    keys += list(config.get("condition_map", {}).values())
    for node in keys:
        if node and node not in AGENT_NODE_REGISTRY:
            raise ValueError(f"Unknown node name in config: '{node}'")


def load_config_profile(profile_name: str) -> AgentConfig:
    """
    load_config_profile.
    :param profile_name: Description of profile_name
    :type profile_name: Any
    :return: Description of return value
    :rtype: Any
    """
    presets_dir = Path("presets")
    profile_path = presets_dir / f"{profile_name}.yaml"
    if not profile_path.exists():
        logger.error(
            f"[config loader] Profile '{profile_name}' not found at {profile_path}."
        )
        raise FileNotFoundError(f"Preset profile '{profile_name}' does not exist.")
    raw_config = yaml.safe_load(profile_path.read_text())
    if "state_type" not in raw_config:
        logger.error(f"[config loader] 'state_type' missing in profile: {profile_name}")
        raise ValueError(f"'state_type' is required in profile '{profile_name}'")
    validate_node_names(raw_config)
    raw_config["state_type"] = resolve_dotted_type(raw_config["state_type"])
    logger.info(f"[config loader] Loaded config profile '{profile_name}' successfully.")
    return AgentConfig(**raw_config)
