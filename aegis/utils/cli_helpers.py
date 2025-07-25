# aegis/utils/cli_helpers.py
"""
Shared logic for CLI commands and their corresponding API endpoints.

This module contains the core implementation for developer-focused actions
like configuration validation and tool scaffolding. By centralizing the
logic here, we ensure that both the interactive shell (shell.py) and the
FastAPI server (routes_dev.py) have consistent behavior.
"""
import importlib.util
import sys
from pathlib import Path

import yaml

from aegis.exceptions import ConfigurationError
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.config import get_config
from aegis.utils.config_loader import load_agent_config
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


def validate_all_configs() -> list:
    """Proactively loads and validates all key configuration files."""
    results = []

    def check(name, action):
        try:
            action()
            results.append({"name": name, "status": "OK"})
        except Exception as e:
            results.append({"name": name, "status": "FAILED", "reason": str(e)})

    check("config.yaml", get_config)

    # Validate all backend profiles
    try:
        backends_path = Path("backends.yaml")
        if backends_path.is_file():
            backend_profiles = yaml.safe_load(backends_path.read_text()).get(
                "backends", []
            )
            for profile in backend_profiles:
                if name := profile.get("profile_name"):
                    check(f"Backend: {name}", lambda p=name: get_backend_config(p))
    except Exception as e:
        results.append({"name": "backends.yaml", "status": "FAILED", "reason": str(e)})

    # Validate all machine profiles
    try:
        machines_path = Path("machines.yaml")
        if machines_path.is_file():
            machine_profiles = yaml.safe_load(machines_path.read_text()) or {}
            for name in machine_profiles:
                check(f"Machine: {name}", lambda n=name: get_machine(n))
    except Exception as e:
        results.append({"name": "machines.yaml", "status": "FAILED", "reason": str(e)})

    # Validate all presets
    presets_dir = Path("presets")
    if presets_dir.is_dir():
        for preset_file in presets_dir.glob("*.yaml"):
            check(
                f"Preset: {preset_file.name}",
                lambda p=preset_file.stem: load_agent_config(profile=p),
            )

    return results


def validate_tool_file(file_path: Path):
    """
    Validates a single tool file by attempting to import it.
    This checks for syntax errors and ensures that the file is importable,
    which is a prerequisite for tool registration to occur.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Tool file not found at: {file_path}")

    module_name = f"aegis.tool_validation.{file_path.stem}"

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not create module spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
        logger.info(f"Successfully validated and imported tool file: {file_path}")
    except Exception as e:
        logger.error(f"Validation failed for {file_path}. Error: {e}")
        raise e
    finally:
        if module_name in sys.modules:
            del sys.modules[module_name]


def _to_pascal_case(snake_str: str) -> str:
    return "".join(word.capitalize() for word in snake_str.split("_"))


def create_new_tool(name: str, description: str, category: str, is_safe: bool) -> Path:
    """Creates a new boilerplate tool file."""
    plugins_dir = Path("plugins")
    plugins_dir.mkdir(exist_ok=True)
    (plugins_dir / "__init__.py").touch(exist_ok=True)

    file_path = plugins_dir / f"{name}.py"
    if file_path.exists():
        raise FileExistsError(f"Tool file '{file_path}' already exists.")

    class_name = f"{_to_pascal_case(name)}Input"
    content = f"""# plugins/{name}.py
from pydantic import BaseModel, Field
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class {class_name}(BaseModel):
    \"\"\"Input model for the {name} tool.

    :ivar example_arg: An example argument for your tool.
    :vartype example_arg: str
    \"\"\"
    example_arg: str = Field(..., description="An example argument for your tool.")


@register_tool(
    name="{name}",
    input_model={class_name},
    description="{description}",
    category="{category}",
    tags=["custom", "{name}"],
    safe_mode={is_safe}
)
def {name}(input_data: {class_name}) -> str:
    \"\"\"{description}

    :param input_data: The validated input data for the tool.
    :type input_data: {class_name}
    :return: A string containing the result of the tool's execution.
    :rtype: str
    \"\"\"
    logger.info(f"Executing tool: {name}")

    # --- YOUR TOOL LOGIC GOES HERE ---
    result = f"Tool '{{name}}' executed with arg: {{input_data.example_arg}}"
    # ---------------------------------

    return result
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path
