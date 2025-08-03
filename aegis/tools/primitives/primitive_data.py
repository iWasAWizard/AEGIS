# aegis/tools/primitives/data.py
"""
Primitive tools for data transformation, parsing, and validation.
"""
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class StringContainsInput(BaseModel):
    """Input model for checking if a string contains a substring.

    :ivar input_string: The larger string to search within.
    :vartype input_string: str
    :ivar substring: The substring to search for.
    :vartype substring: str
    """

    input_string: str = Field(..., description="The larger string to search within.")
    substring: str = Field(..., description="The substring to search for.")


# === Tools ===


@register_tool(
    name="string_contains",
    input_model=StringContainsInput,
    description="Checks if a given input string contains a specific substring. Returns 'True' or 'False'.",
    tags=["string", "validation", "primitive", "data"],
    category="data",
    safe_mode=True,
    purpose="Check for the presence of a substring within a larger string.",
)
def string_contains(input_data: StringContainsInput) -> bool:
    """
    Performs a substring check and returns a boolean value.

    :param input_data: An object containing the input string and the substring to check for.
    :type input_data: StringContainsInput
    :return: True if the substring is found, False otherwise.
    :rtype: bool
    """
    logger.info(
        f"Checking if '{input_data.substring}' is in string '{input_data.input_string[:100]}...'"
    )
    return input_data.substring in input_data.input_string
