# aegis/tools/primitives/chaos.py
"""
Primitive tools for generating random, chaotic, or unpredictable data.

This module provides a suite of tools useful for testing, fuzzing, and creating
mock data. It includes functions for generating random strings, numbers, choices,
and for intentionally corrupting data structures like JSON.
"""

import random
import string
import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.schemas.emoji import EMOJI_SET
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===

class RandomStringInput(BaseModel):
    """Input for generating a random string."""
    length: int = Field(..., gt=0, description="The desired length of the string.")
    charset: str = Field(
        "alphanum",
        description="The character set to use: 'ascii', 'hex', 'digits', 'alphanum', or 'emoji'.",
    )


class RandomNumberInput(BaseModel):
    """Input for generating a random number within a specified range."""
    min_value: float = Field(..., description="The minimum possible value (inclusive).")
    max_value: float = Field(..., description="The maximum possible value (inclusive).")
    as_int: bool = Field(False, description="If True, the result will be cast to an integer.")


class RandomBoolInput(BaseModel):
    """Input for generating a random boolean value."""
    p_true: float = Field(0.5, ge=0.0, le=1.0, description="The probability of returning True.")


class UUIDInput(BaseModel):
    """Input for generating a Universally Unique Identifier (UUID)."""
    namespace: Optional[str] = Field(None, description="An optional namespace for generating a deterministic UUIDv5.")


class RandomChoiceInput(BaseModel):
    """Input for selecting a random item from a list."""
    choices: List[str] = Field(..., min_length=1, description="A list of strings to choose from.")


class CorruptJSONInput(BaseModel):
    """Input for intentionally corrupting a JSON string."""
    json_string: str = Field(..., description="A valid JSON string to be corrupted.")
    severity: str = Field("medium", description="The level of corruption: 'low', 'medium', or 'high'.")


# === Tools ===

@register_tool(
    name="random_string",
    input_model=RandomStringInput,
    description="Generate a random string of a given length and from a specified character set.",
    tags=["random", "string", "test", "primitive"],
    category="primitive",
    purpose="Create random string data for testing or mock payloads.",
    safe_mode=True,
)
def random_string(input_data: RandomStringInput) -> str:
    """Generates a random string based on the provided length and charset.

    :param input_data: An object containing the length and charset for the string.
    :type input_data: RandomStringInput
    :return: The generated random string.
    :rtype: str
    """
    charset_map = {
        "ascii": string.ascii_letters,
        "hex": string.hexdigits,
        "digits": string.digits,
        "alphanum": string.ascii_letters + string.digits,
        "emoji": EMOJI_SET,
    }
    chars = charset_map.get(input_data.charset, string.ascii_letters + string.digits)
    return "".join(random.choices(chars, k=input_data.length))


@register_tool(
    name="random_number",
    input_model=RandomNumberInput,
    description="Generate a random number (float or integer) between two values.",
    tags=["random", "number", "test", "primitive"],
    category="primitive",
    purpose="Create a random numeric value within a specific range.",
    safe_mode=True,
)
def random_number(input_data: RandomNumberInput) -> Union[float, int]:
    """Generates a random number within a given range.

    :param input_data: An object containing the min/max values and integer flag.
    :type input_data: RandomNumberInput
    :return: A random float or integer.
    :rtype: Union[float, int]
    """
    value = random.uniform(input_data.min_value, input_data.max_value)
    return int(value) if input_data.as_int else value


@register_tool(
    name="random_bool",
    input_model=RandomBoolInput,
    description="Return True or False with a specified probability.",
    tags=["random", "bool", "test", "primitive"],
    category="primitive",
    purpose="Generate a random boolean value, useful for toggling flags.",
    safe_mode=True,
)
def random_bool(input_data: RandomBoolInput) -> bool:
    """Generates a random boolean with a given probability of being True.

    :param input_data: An object containing the probability of True.
    :type input_data: RandomBoolInput
    :return: A random boolean value.
    :rtype: bool
    """
    return random.random() < input_data.p_true


@register_tool(
    name="random_choice",
    input_model=RandomChoiceInput,
    description="Pick a random item from a provided list of strings.",
    tags=["random", "choice", "test", "primitive"],
    category="primitive",
    purpose="Select one item randomly from a list of options.",
    safe_mode=True,
)
def random_choice(input_data: RandomChoiceInput) -> str:
    """Picks one item at random from the provided list.

    :param input_data: An object containing the list of choices.
    :type input_data: RandomChoiceInput
    :return: A single item chosen from the list.
    :rtype: str
    """
    return random.choice(input_data.choices)


@register_tool(
    name="generate_uuid",
    input_model=UUIDInput,
    description="Generate a UUID (v4 for random, or v5 if a namespace is provided).",
    tags=["random", "uuid", "test", "primitive"],
    category="primitive",
    purpose="Create a universally unique identifier.",
    safe_mode=True,
)
def generate_uuid(input_data: UUIDInput) -> str:
    """Generates a UUID.

    :param input_data: An object that can optionally contain a namespace.
    :type input_data: UUIDInput
    :return: The generated UUID as a string.
    :rtype: str
    """
    if input_data.namespace:
        # Generate a deterministic UUIDv5 based on a namespace and name.
        namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, input_data.namespace)
        return str(uuid.uuid5(namespace_uuid, "entity"))
    # Generate a random UUIDv4.
    return str(uuid.uuid4())


@register_tool(
    name="corrupt_json",
    input_model=CorruptJSONInput,
    description="Intentionally corrupts a JSON string by inserting syntax errors.",
    tags=["chaos", "fuzz", "corrupt", "primitive"],
    category="primitive",
    purpose="Test JSON parsers by providing them with malformed input.",
    safe_mode=True,
)
def corrupt_json(input_data: CorruptJSONInput) -> str:
    """Intentionally breaks a valid JSON string.

    :param input_data: An object containing the JSON string and corruption severity.
    :type input_data: CorruptJSONInput
    :return: A corrupted, likely invalid, JSON string.
    :rtype: str
    """
    logger.debug(f"Corrupting JSON (severity={input_data.severity})")
    corrupted = input_data.json_string
    if input_data.severity in ["medium", "high"]:
        # Introduce common syntax errors
        corrupted = corrupted.replace(":", " = ", 1)  # Invalid assignment
        corrupted = corrupted.replace('"', "", 1)  # Unmatched quote
    if input_data.severity == "high":
        # Add junk characters at the end
        corrupted += random.choice(["}", ",", " [", "NULL", " 💩"])
    return corrupted
