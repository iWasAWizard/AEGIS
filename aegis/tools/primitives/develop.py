"""Development and testing tools used for internal agent validation and runtime scaffolding."""

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class EchoInputModel(BaseModel):
    """
    Represents the EchoInputModel class.

    Used as the input schema for the `echo_input` tool, primarily for testing and development.
    """

    payload: dict = Field(..., description="Payload to echo back")


class NoOpModel(BaseModel):
    """
    Represents the NoOpModel class.

    An empty model used for tools that perform no action or require no input.
    """

    dummy: str = Field(..., description="A placeholder field, ignored.")


@register_tool(
    name="echo_input",
    input_model=EchoInputModel,
    description="Returns the input payload unchanged.",
    tags=["test", "dev"],
    category="primitive",
    safe_mode=True,
)
def echo_input(input_data: EchoInputModel) -> dict:
    """
    echo_input.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug(f"Echoing payload: {input_data.payload}")
    return input_data.payload


@register_tool(
    name="no_op",
    input_model=NoOpModel,
    description="Returns a static OK response.",
    tags=["test", "dev"],
    category="primitive",
    safe_mode=True,
)
def no_op(_: NoOpModel) -> str:
    """
    no_op.
    :param _: Description of _
    :type _: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug("NoOp tool invoked")
    return "ok"
