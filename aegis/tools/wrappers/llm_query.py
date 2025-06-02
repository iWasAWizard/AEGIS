from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class EvaluateArgumentInput(BaseModel):
    """
    EvaluateArgumentInput class.
    """

    argument: str = Field(..., description="Statement or reasoning to evaluate.")


class LLMQueryInput(BaseModel):
    """
    LLMQueryInput class.
    """

    user_prompt: str = Field(..., description="The question or request to ask the LLM")
    system_prompt: str = Field(
        "You are a helpful assistant.",
        description="System-level behavior instruction for the LLM",
    )


class SummarizeTextInput(BaseModel):
    """
    SummarizeTextInput class.
    """

    long_text: str = Field(..., description="The content to summarize.")


class RewriteTextInput(BaseModel):
    """
    RewriteTextInput class.
    """

    text: str = Field(..., description="Text to rewrite for clarity.")


class ExtractActionItemsInput(BaseModel):
    """
    ExtractActionItemsInput class.
    """

    text: str = Field(..., description="Text or notes to extract action items from.")


class ExplainCodeInput(BaseModel):
    """
    ExplainCodeInput class.
    """

    code_snippet: str = Field(..., description="Code snippet to explain.")


class GenerateTestsInput(BaseModel):
    """
    GenerateTestsInput class.
    """

    code: str = Field(..., description="Code to generate tests for.")


@register_tool(
    name="invoke_llm_query",
    input_model=LLMQueryInput,
    tags=["llm", "reasoning", "query"],
    description="Invoke the current Ollama LLM with a prompt using the correct chat template.",
    safe_mode=True,
    category="LLM"
)
def invoke_llm_query(input_data: LLMQueryInput) -> str:
    """
    invoke_llm_query.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Invoking LLM query with system prompt and user prompt")
    logger.debug(f"System Prompt: {input_data.system_prompt}")
    logger.debug(f"User Prompt: {input_data.user_prompt}")
    result = await llm_query(system_prompt=input_data.system_prompt, user_prompt=input_data.user_prompt)
    logger.debug(f"LLM Response: {result}")
    return result


@register_tool(
    name="summarize_text",
    input_model=SummarizeTextInput,
    tags=["llm", "summarization", "compression"],
    description="Summarize a long body of text using the LLM.",
    safe_mode=True,
    category="LLM"
)
def summarize_text(input_data: SummarizeTextInput) -> str:
    """
    summarize_text.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You are a helpful assistant that summarizes content clearly and concisely.",
        user_prompt=f"Summarize the following:\n\n{input_data.long_text}",
    )


@register_tool(
    name="rewrite_for_readability",
    input_model=RewriteTextInput,
    tags=["llm", "rewrite", "readability"],
    description="Rewrite content to make it more understandable.",
    safe_mode=True,
    category="LLM"
)
def rewrite_for_readability(input_data: RewriteTextInput) -> str:
    """
    rewrite_for_readability.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You rewrite technical content for clarity and ease of understanding.",
        user_prompt=f"Rewrite this to be easier to understand:\n\n{input_data.text}",
    )


@register_tool(
    name="extract_action_items",
    input_model=ExtractActionItemsInput,
    tags=["llm", "analysis", "extraction", "tasks"],
    description="Extract next steps or tasks from unstructured text.",
    safe_mode=True,
    category="LLM"
)
def extract_action_items(input_data: ExtractActionItemsInput) -> str:
    """
    extract_action_items.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You identify and list action items from long-form discussions.",
        user_prompt=f"Extract action items from this:\n\n{input_data.text}",
    )


@register_tool(
    name="explain_code",
    input_model=ExplainCodeInput,
    tags=["llm", "code", "explanation"],
    description="Provide a plain-English explanation of a code snippet.",
    safe_mode=True,
    category="LLM"
)
def explain_code(input_data: ExplainCodeInput) -> str:
    """
    explain_code.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You are a professional code reviewer who explains code in plain English.",
        user_prompt=f"Explain what this code does:\n\n{input_data.code_snippet}",
    )


@register_tool(
    name="generate_tests_for_code",
    input_model=GenerateTestsInput,
    tags=["llm", "code", "testing", "generation"],
    description="Use LLM to generate pytest-style unit tests.",
    safe_mode=True,
    category="LLM"
)
def generate_tests_for_code(input_data: GenerateTestsInput) -> str:
    """
    generate_tests_for_code.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You write unit tests in Python using pytest.",
        user_prompt=f"Write unit tests for the following function:\n\n{input_data.code}",
    )


@register_tool(
    name="evaluate_argument",
    input_model=EvaluateArgumentInput,
    tags=["llm", "analysis", "reasoning", "logic"],
    description="Critique an argument or opinion for logic, coherence, and clarity.",
    safe_mode=True,
    category="LLM"
)
def evaluate_argument(input_data: EvaluateArgumentInput) -> str:
    """
    evaluate_argument.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    return llm_query(
        system_prompt="You are a formal logic tutor. Evaluate arguments for soundness and clarity.",
        user_prompt=f"Evaluate this argument:\n\n{input_data.argument}",
    )
