# aegis/tools/wrappers/generative_tools.py
"""
High-level tools for invoking the agent's primary LLM to perform specific,
common generative tasks.

This module provides a suite of tools that wrap the core `llm_query` utility,
presenting it to the agent for tasks like summarization, code explanation,
and logical evaluation. These tools use pre-defined system prompts to guide
the LLM's behavior for a specific purpose.
"""

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class LLMQueryInput(BaseModel):
    """Input for making a generic query to the LLM.

    :ivar user_prompt: The question or request to ask the LLM.
    :vartype user_prompt: str
    :ivar system_prompt: System-level behavior instruction for the LLM.
    :vartype system_prompt: str
    """
    user_prompt: str = Field(..., description="The question or request to ask the LLM.")
    system_prompt: str = Field("You are a helpful assistant.",
                               description="System-level behavior instruction for the LLM.")


class TextContentInput(BaseModel):
    """A generic input model for tools that operate on a block of text.

    :ivar text: The text content to process.
    :vartype text: str
    """
    text: str = Field(..., description="The text content to process.")


class CodeContentInput(BaseModel):
    """A generic input model for tools that operate on a block of code.

    :ivar code: The code snippet to process.
    :vartype code: str
    """
    code: str = Field(..., description="The code snippet to process.")


# === Tools ===


@register_tool(name="invoke_llm_query", input_model=LLMQueryInput, tags=["llm", "reasoning", "query", "wrapper"],
               description="Invoke the system's LLM with a custom system and user prompt.", safe_mode=True,
               purpose="Perform a generic query or reasoning task using the main LLM.", category="LLM")
async def invoke_llm_query(input_data: LLMQueryInput) -> str:
    """A direct, tool-based interface to the core `llm_query` utility.

    :param input_data: An object containing the system and user prompts.
    :type input_data: LLMQueryInput
    :return: The response from the language model.
    :rtype: str
    """
    logger.info("Invoking LLM query via tool with custom prompts.")
    return await llm_query(system_prompt=input_data.system_prompt, user_prompt=input_data.user_prompt)


@register_tool(name="summarize_text", input_model=TextContentInput,
               tags=["llm", "summarization", "compression", "wrapper"],
               description="Summarize a long body of text using the LLM.", safe_mode=True,
               purpose="Create a concise summary of a large block of text.", category="LLM")
async def summarize_text(input_data: TextContentInput) -> str:
    """Uses the LLM to summarize the provided text.

    :param input_data: An object containing the text to be summarized.
    :type input_data: TextContentInput
    :return: The summarized text.
    :rtype: str
    """
    logger.info("Requesting LLM to summarize text.")
    system_prompt = "You are an expert summarizer. Your task is to read the following text and produce a clear, concise summary that captures the main points."
    return await llm_query(system_prompt=system_prompt, user_prompt=input_data.text)


@register_tool(name="rewrite_for_readability", input_model=TextContentInput,
               tags=["llm", "rewrite", "readability", "wrapper"],
               description="Rewrites text to make it more clear and understandable.", safe_mode=True,
               purpose="Improve the clarity and readability of a piece of text.", category="LLM")
async def rewrite_for_readability(input_data: TextContentInput) -> str:
    """Uses the LLM to rewrite text for better readability.

    :param input_data: An object containing the text to be rewritten.
    :type input_data: TextContentInput
    :return: The rewritten text.
    :rtype: str
    """
    logger.info("Requesting LLM to rewrite text for readability.")
    system_prompt = "You are an expert technical writer. Your task is to rewrite the following text to make it clearer, more readable, and easier for a non-expert to understand. Retain the core meaning."
    return await llm_query(system_prompt=system_prompt, user_prompt=f"Please rewrite this:\n\n{input_data.text}")


@register_tool(name="extract_action_items", input_model=TextContentInput,
               tags=["llm", "analysis", "extraction", "tasks", "wrapper"],
               description="Extracts a list of action items or tasks from unstructured text.", safe_mode=True,
               purpose="Identify and list actionable tasks from meeting notes or discussions.", category="LLM")
async def extract_action_items(input_data: TextContentInput) -> str:
    """Uses the LLM to identify and list action items from text.

    :param input_data: An object containing the text to analyze.
    :type input_data: TextContentInput
    :return: A list of extracted action items, typically as a formatted string.
    :rtype: str
    """
    logger.info("Requesting LLM to extract action items from text.")
    system_prompt = "You are an expert at identifying action items. Read the following text and extract a numbered list of all tasks, decisions, or follow-up actions mentioned. If no action items are present, respond with 'No action items found.'"
    return await llm_query(system_prompt=system_prompt,
                           user_prompt=f"Extract action items from this:\n\n{input_data.text}")


@register_tool(name="explain_code", input_model=CodeContentInput, tags=["llm", "code", "explanation", "wrapper"],
               description="Provides a plain-English explanation of a code snippet.", safe_mode=True,
               purpose="Understand what a piece of code does.", category="LLM")
async def explain_code(input_data: CodeContentInput) -> str:
    """Uses the LLM to explain a snippet of code.

    :param input_data: An object containing the code to be explained.
    :type input_data: CodeContentInput
    :return: A natural language explanation of the code.
    :rtype: str
    """
    logger.info("Requesting LLM to explain a code snippet.")
    system_prompt = "You are an expert code reviewer who excels at explaining complex code in simple terms. Provide a clear, high-level explanation of what the following code does."
    return await llm_query(system_prompt=system_prompt,
                           user_prompt=f"Explain this code:\n\n```\n{input_data.code}\n```")


@register_tool(name="generate_tests_for_code", input_model=CodeContentInput,
               tags=["llm", "code", "testing", "generation", "wrapper"],
               description="Uses the LLM to generate unit tests for a given code snippet.", safe_mode=True,
               purpose="Create unit tests for a function or class.", category="LLM")
async def generate_tests_for_code(input_data: CodeContentInput) -> str:
    """Uses the LLM to generate unit tests for a piece of code.

    :param input_data: An object containing the code to generate tests for.
    :type input_data: CodeContentInput
    :return: A string containing the generated unit tests, typically in pytest format.
    :rtype: str
    """
    logger.info("Requesting LLM to generate unit tests for code.")
    system_prompt = "You are a senior software engineer who writes high-quality unit tests. Your task is to write a set of tests for the following Python code using the `pytest` framework. The tests should be complete, runnable, and cover key edge cases."
    return await llm_query(system_prompt=system_prompt,
                           user_prompt=f"Write pytest unit tests for this code:\n\n```python\n{input_data.code}\n```")
