import random
import string
import uuid
from typing import List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger
from aegis.schemas.emoji import EMOJI_SET

logger = setup_logger(__name__)

load_dotenv()


class RandomStringInput(BaseModel):
    """
    Represents the RandomStringInput class.

    Specifies input parameters for generating a random string using a specific charset and length.
    """

    length: int = Field(..., gt=0, description="Length of the generated string")
    charset: Optional[str] = Field(
        "alphanum", description="Charset: ascii, hex, digits, alphanum, emoji"
    )


class RandomNumberInput(BaseModel):
    """
    RandomNumberInput class.
    """

    min_value: float = Field(..., description="Minimum number")
    max_value: float = Field(..., description="Maximum number")
    as_int: bool = Field(False, description="Return as integer")


class RandomBoolInput(BaseModel):
    """
    RandomBoolInput class.
    """

    p_true: float = Field(
        0.5, ge=0.0, le=1.0, description="Probability of returning True"
    )


class UUIDInput(BaseModel):
    """
    UUIDInput class.
    """

    namespace: Optional[str] = Field(
        None, description="Optional namespace seed for deterministic UUIDs"
    )


class RandomChoiceInput(BaseModel):
    """
    RandomChoiceInput class.
    """

    choices: List[str] = Field(
        ..., min_items=1, description="List of items to choose from"
    )


class ChaosRollInput(BaseModel):
    """
    ChaosRollInput class.
    """

    explode: bool = Field(False, description="If true, reroll on 100")
    faces: int = Field(..., description="Max possible roll")


class CorruptJSONInput(BaseModel):
    """
    CorruptJSONInput class.
    """

    json_string: str = Field(..., description="A valid JSON string")
    severity: str = Field("medium", description="low, medium, high")


class InjectNoiseInput(BaseModel):
    """
    InjectNoiseInput class.
    """

    data: Union[str, dict] = Field(..., description="Original data to mangle")
    noise_level: str = Field("medium", description="low, medium, high")


class RandomSentenceInput(BaseModel):
    """
    RandomSentenceInput class.
    """

    min_words: int = Field(3, ge=1)
    max_words: int = Field(12, ge=1)
    include_emoji: bool = Field(False)


class FuzzDictInput(BaseModel):
    """
    FuzzDictInput class.
    """

    keys: List[str] = Field(..., min_items=1)
    length: int = Field(3, ge=1)


@register_tool(
    name="random_string",
    input_model=RandomStringInput,
    description="Generate a random string of a given length and character set.",
    tags=["random", "string", "test"],
    category="primitive",
    safe_mode=True,
)
def random_string(input_data: RandomStringInput) -> str:
    """
    random_string.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    length = input_data.length
    cs = input_data.charset
    if cs == "ascii":
        chars = string.ascii_letters
    elif cs == "hex":
        chars = string.hexdigits
    elif cs == "digits":
        chars = string.digits
    elif cs == "emoji":
        chars = EMOJI_SET
    else:
        chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


@register_tool(
    name="random_number",
    input_model=RandomNumberInput,
    description="Generate a random number between two values.",
    tags=["random", "number", "test"],
    category="primitive",
    safe_mode=True,
)
def random_number(input_data: RandomNumberInput):
    """
    random_number.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    value = random.uniform(input_data.min_value, input_data.max_value)
    return int(value) if input_data.as_int else value


@register_tool(
    name="random_bool",
    input_model=RandomBoolInput,
    description="Return True or False with an optional probability bias.",
    tags=["random", "bool", "test"],
    category="primitive",
    safe_mode=True,
)
def random_bool(input_data: RandomBoolInput) -> bool:
    """
    random_bool.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return random.random() < input_data.p_true


@register_tool(
    name="random_choice",
    input_model=RandomChoiceInput,
    description="Pick a random item from a provided list.",
    tags=["random", "choice", "test"],
    category="primitive",
    safe_mode=True,
)
def random_choice(input_data: RandomChoiceInput) -> str:
    """
    random_choice.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return random.choice(input_data.choices)


@register_tool(
    name="generate_uuid",
    input_model=UUIDInput,
    description="Generate a UUID (v4 or v5 if namespaced).",
    tags=["random", "uuid", "test"],
    category="primitive",
    safe_mode=True,
)
def generate_uuid(input_data: UUIDInput) -> str:
    """
    generate_uuid.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    if input_data.namespace:
        ns = uuid.uuid5(uuid.NAMESPACE_DNS, input_data.namespace)
        return str(uuid.uuid5(ns, "entity"))
    return str(uuid.uuid4())


COMMON_WORDS = [
    "system",
    "panic",
    "goat",
    "launch",
    "error",
    "input",
    "forgot",
    "emoji",
    "chaos",
    "data",
]


@register_tool(
    name="random_sentence",
    input_model=RandomSentenceInput,
    description="Generate a random sentence from shuffled words and emoji.",
    tags=["chaos", "mock", "string"],
    category="primitive",
    safe_mode=True,
)
def random_sentence(input_data: RandomSentenceInput) -> str:
    """
    random_sentence.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug("Generating random character string.")

    num_words = random.randint(input_data.min_words, input_data.max_words)
    words = random.choices(COMMON_WORDS, k=num_words)
    if input_data.include_emoji:
        words += random.choices(EMOJI_SET, k=random.randint(1, 3))
    random.shuffle(words)
    return " ".join(words).capitalize() + "."


@register_tool(
    name="fuzz_dict",
    input_model=FuzzDictInput,
    description="Create a random dict with specified keys and randomized values.",
    tags=["chaos", "fuzz", "dict"],
    category="primitive",
    safe_mode=True,
)
def fuzz_dict(input_data: FuzzDictInput) -> dict:
    """
    fuzz_dict.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return {
        key: random.choice(
            [
                random.randint(0, 9999),
                random.uniform(0, 1000),
                random.choice(["alpha", "beta", "chaotic", "zeta"]),
                random_sentence(
                    RandomSentenceInput(min_words=2, max_words=5, include_emoji=False)
                ),
            ]
        )
        for key in random.choices(input_data.keys, k=input_data.length)
    }


@register_tool(
    name="inject_noise",
    input_model=InjectNoiseInput,
    description="Inject typos, junk keys, or emoji into a string or dict.",
    tags=["chaos", "fuzz", "corrupt"],
    category="primitive",
    safe_mode=True,
)
def inject_noise(input_data: InjectNoiseInput):
    """
    inject_noise.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """

    def corrupt_string(s):
        """
        corrupt_string.
        :param s: Description of s
        :type s: Any
        :return: Description of return value
        :rtype: Any
        """
        replacements = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "$", "t": "+"}
        return "".join((replacements.get(c, c) for c in s))

    if isinstance(input_data.data, str):
        noisy = corrupt_string(input_data.data)
        if input_data.noise_level != "low":
            noisy += random.choice([" 🤡", " 🚨", " 💥"])
        return noisy
    if isinstance(input_data.data, dict):
        corrupted = {}
        for k, v in input_data.data.items():
            new_key = corrupt_string(k) if input_data.noise_level != "low" else k
            new_val = corrupt_string(str(v)) if isinstance(v, str) else v
            corrupted[new_key] = new_val
        if input_data.noise_level in ["medium", "high"]:
            for _ in range(random.randint(1, 3)):
                corrupted[random.choice(EMOJI_SET) + "_junk"] = random.choice(
                    ["💣", "⚠️", 42, "null"]
                )
        return corrupted
    return input_data.data


@register_tool(
    name="chaos_roll",
    input_model=ChaosRollInput,
    description="Roll a 100-sided die and return the result with a chaotic description.",
    tags=["chaos, fuzz, random"],
    category="primitive",
    safe_mode=False,
)
def chaos_roll(input_data: ChaosRollInput):
    """
    chaos_roll.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Rolling d{input_data.faces} for initiative.")
    total = 0
    rolls = []
    roll = random.randint(1, input_data.faces)
    logger.info(f"Rolled a {roll} / {input_data.faces}")
    total += roll
    rolls.append(roll)
    while input_data.explode and roll == 100:
        roll = random.randint(1, 100)
        total += roll
        rolls.append(roll)
    if total < 20:
        label = "💀 catastrophic failure"
    elif total < 50:
        label = "⚠️ minor glitch"
    elif total < 80:
        label = "✅ safe passage"
    elif total < 100:
        label = "🎉 impressive"
    else:
        label = "🌈 divine intervention"
    return {"rolls": rolls, "total": total, "outcome": label}


@register_tool(
    name="corrupt_json",
    input_model=CorruptJSONInput,
    description="Intentionally corrupt a JSON string by inserting syntax errors.",
    tags=["chaos", "fuzz", "corrupt"],
    category="primitive",
    safe_mode=True,
)
def corrupt_json(input_data: CorruptJSONInput) -> str:
    """
    corrupt_json.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug(f"Corrupting JSON (severity={input_data.severity})")
    corrupted = input_data.json_string
    if input_data.severity in ["medium", "high"]:
        corrupted = corrupted.replace(":", " = ", 1)
        corrupted = corrupted.replace('"', "", 1)
    if input_data.severity == "high":
        corrupted += random.choice(["}", ",", " [", "NULL", " 💩"])
    return corrupted
