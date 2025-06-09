# aegis/tools/primitives/develop.py
"""Development and testing tools used for internal agent validation and runtime scaffolding."""

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class EchoInputModel(BaseModel):
    """Input model for the echo_input tool.

    :ivar payload: A dictionary payload to be echoed back by the tool.
    :vartype payload: dict
    """

    payload: dict = Field(..., description="Payload to echo back")


class NoOpModel(BaseModel):
    """An empty input model for tools that require no arguments."""

    pass


@register_tool(
    name="echo_input",
    input_model=EchoInputModel,
    description="Returns the input payload unchanged. Useful for testing.",
    tags=["test", "dev", "primitive"],
    category="primitive",
    safe_mode=True,
    purpose="Echo back a given payload for testing data flow.",
)
def echo_input(input_data: EchoInputModel) -> dict:
    """A simple tool that returns its input data.

    This tool is primarily used for debugging and testing to verify that
    data is being passed correctly through the agent's execution graph.

    :param input_data: The data to be echoed.
    :type input_data: EchoInputModel
    :return: The original payload from the input data.
    :rtype: dict
    """
    logger.debug(f"Echoing payload: {input_data.payload}")
    return input_data.payload


@register_tool(
    name="no_op",
    input_model=NoOpModel,
    description="Performs no action and returns a static 'ok' response. Useful for testing graph flow.",
    tags=["test", "dev", "primitive"],
    category="primitive",
    safe_mode=True,
    purpose="Perform a no-op action for graph flow testing.",
)
def no_op(_: NoOpModel) -> str:
    """A tool that does nothing and confirms its execution.

    This is useful for creating placeholder nodes in an agent graph or for
    testing the graph's transition logic without performing any real actions.

    :param _: An empty input model, which is ignored.
    :type _: NoOpModel
    :return: A static string "ok".
    :rtype: str
    """
    logger.debug("NoOp tool invoked")
    return "ok"
