# aegis/tools/wrappers/agentic.py
"""
Wrapper tools for agent-to-agent communication and delegation.
"""
import json

import requests
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class DispatchSubtaskInput(BaseModel):
    """Input for dispatching a sub-task to another specialized agent.

    :ivar prompt: The natural language prompt for the sub-task.
    :vartype prompt: str
    :ivar preset: The agent preset to use for the sub-task (e.g., 'default', 'verified_flow').
    :vartype preset: str
    :ivar backend_profile: The backend profile for the sub-agent to use.
    :vartype backend_profile: str
    """

    prompt: str = Field(
        ..., description="The natural language prompt for the sub-task."
    )
    preset: str = Field(
        "default",
        description="The agent preset to use for the sub-task (e.g., 'default', 'verified_flow').",
    )
    backend_profile: str = Field(
        ..., description="The backend profile for the sub-agent to use."
    )


@register_tool(
    name="dispatch_subtask_to_agent",
    input_model=DispatchSubtaskInput,
    description="Delegates a specific, self-contained sub-task to a specialized agent and returns its final summary. Use this for complex tasks that can be broken down.",
    category="agentic",
    tags=["agent", "delegation", "subtask", "wrapper"],
    safe_mode=True,  # The tool itself is safe; safety of the sub-task is governed by its own context.
    purpose="Delegate a complex sub-task to a specialist agent.",
)
def dispatch_subtask_to_agent(input_data: DispatchSubtaskInput) -> str:
    """
    Invokes another AEGIS agent via the API to perform a sub-task.

    This tool makes a synchronous HTTP POST request to its own /api/launch
    endpoint, effectively creating a hierarchical agent structure. It waits for
    the sub-agent to complete its task and returns the summary.

    :param input_data: The prompt, preset, and backend for the sub-task.
    :type input_data: DispatchSubtaskInput
    :return: The final summary from the sub-agent's execution.
    :rtype: str
    :raises ToolExecutionError: If the API call fails or the sub-agent returns an error.
    """
    logger.info(
        f"Dispatching sub-task to agent with preset '{input_data.preset}': '{input_data.prompt[:50]}...'"
    )

    # The agent calls itself. We assume it's running on localhost at port 8000.
    # A more advanced version could get this from a service discovery mechanism.
    launch_url = "http://localhost:8000/api/launch"

    payload = {
        "task": {"prompt": input_data.prompt},
        "config": input_data.preset,
        "execution": {"backend_profile": input_data.backend_profile},
    }

    try:
        response = requests.post(
            launch_url, json=payload, timeout=900
        )  # 15 min timeout
        response.raise_for_status()
        result = response.json()

        summary = result.get("summary", "Sub-agent did not provide a summary.")
        logger.info(
            f"Sub-task completed successfully. Returning summary to orchestrator."
        )
        return summary

    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json().get("detail", e.response.text)
        logger.error(f"Sub-agent task failed with HTTP error: {error_detail}")
        raise ToolExecutionError(f"Sub-agent task failed: {error_detail}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to the AEGIS API for sub-task: {e}")
        raise ToolExecutionError(
            f"Could not dispatch sub-task due to a network error: {e}"
        )
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response from sub-agent API.")
        raise ToolExecutionError("Sub-agent returned an invalid JSON response.")
