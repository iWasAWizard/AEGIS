# aegis/utils/prompt_formatter.py
"""
Centralized prompt formatting utility to support multiple LLM chat templates.

This module ensures that the conversation history sent to the language model
is formatted according to the specific requirements of the target model family
(e.g., Llama 3, Mistral), which is crucial for optimal performance.
"""
from typing import List, Dict, Any

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _format_llama3(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts using the Llama 3 instruction template.

    :param messages: A list of message dictionaries.
    :type messages: List[Dict[str, Any]]
    :return: A single string formatted for a Llama 3 model.
    :rtype: str
    """
    prompt = "<|begin_of_text|>"
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    # Add the prompt for the assistant's turn
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt


def _format_chatml(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts using the ChatML template (used by Mistral, Qwen, many others).

    :param messages: A list of message dictionaries.
    :type messages: List[Dict[str, Any]]
    :return: A single string formatted in ChatML.
    :rtype: str
    """
    prompt = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    # Add the prompt for the assistant's turn
    prompt += "<|im_start|>assistant\n"
    return prompt


def _format_alpaca_vicuna(messages: List[Dict[str, Any]]) -> str:
    """
    Formats prompts using a common Alpaca/Vicuna-style template.
    Example:
    SYSTEM: You are a helpful AI assistant.
    USER: Hello, how are you?
    ASSISTANT: I'm doing great. How can I help you today?

    (System prompt is often prepended directly)
    """
    prompt = ""
    system_message_content = ""

    # Extract system message first if present
    # Alpaca often just prepends it, or it's implicitly part of the first user turn.
    # Vicuna is more explicit with "SYSTEM:"
    temp_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_message_content = msg["content"] + "\n"
        else:
            temp_messages.append(msg)

    prompt += system_message_content

    for msg in temp_messages:
        role_upper = msg["role"].upper()
        # Use USER: and ASSISTANT: convention
        if role_upper == "USER":
            prompt += f"USER: {msg['content']}\n"
        elif role_upper == "ASSISTANT":
            prompt += f"ASSISTANT: {msg['content']}\n"
        # else: # Other roles might not be standard in this format
        #     prompt += f"{role_upper}: {msg['content']}\n"

    prompt += "ASSISTANT: "  # Prompt for the assistant's turn
    return prompt.strip() + "\n"


def _format_phi3(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts using the Phi-3 chat template.
    <|user|>
    How to install a Python package?<|end|>
    <|assistant|>
    You can install a Python package using pip...<|end|>
    """
    prompt_parts = []
    # Phi-3 technically doesn't have a distinct "system" role in its prompt structure,
    # it's usually part of the first user message or an initial assistant message.
    # We will prepend any system message to the first user message content.
    system_content = ""
    processed_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_content += msg["content"] + "\n"
        else:
            processed_messages.append(msg)

    if (
        system_content
        and processed_messages
        and processed_messages[0]["role"] == "user"
    ):
        processed_messages[0]["content"] = (
            system_content + processed_messages[0]["content"]
        )
    elif system_content:
        prompt_parts.append(f"<|user|>\n{system_content.strip()}<|end|>")

    for msg in processed_messages:
        role = msg["role"]
        content = msg["content"].strip()
        if role == "user":
            prompt_parts.append(f"<|user|>\n{content}<|end|>")
        elif role == "assistant":
            prompt_parts.append(f"<|assistant|>\n{content}<|end|>")
        # Other roles not standard for Phi-3

    prompt_parts.append("<|assistant|>")
    return "\n".join(prompt_parts)


def _format_codellama_instruct(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts for CodeLlama Instruct models (original format).
    [INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]
    """
    system_prompt_str = "You are a helpful coding assistant."
    user_prompts_content = []

    # Extract system prompt and concatenate user messages
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            system_prompt_str = msg["content"]
        elif msg["role"] == "user":
            user_prompts_content.append(msg["content"])
        elif msg["role"] == "assistant":
            # If there's an assistant message, it implies a multi-turn setup for few-shot.
            # The format is [INST] user [/INST] assistant [INST] user2 [/INST] assistant2 ...
            # This simple formatter will combine all user prompts before the final [/INST]
            # and assume the last turn is for the assistant to complete.
            # For robust multi-turn CodeLlama, this might need more sophistication.
            # For now, we'll append assistant's response to the previous user prompt string.
            if user_prompts_content:
                user_prompts_content[-1] += f" [/INST] {msg['content']}\n[INST] "
            else:
                pass

    if not user_prompts_content:
        if system_prompt_str != "You are a helpful coding assistant.":
            user_prompts_content.append(system_prompt_str)
            system_prompt_str = "You are a helpful coding assistant."
        else:
            user_prompts_content.append("Write a simple hello world program in Python.")

    full_user_prompt = "\n".join(user_prompts_content).strip()

    # Construct the prompt
    # The structure depends on whether there was a system prompt explicitly.
    # LlamaCPP server and HuggingFace often handle <<SYS>> automatically if you just provide system message.
    # But for raw string, we build it.
    if system_prompt_str:
        prompt = f"[INST] <<SYS>>\n{system_prompt_str}\n<</SYS>>\n\n{full_user_prompt} [/INST]"
    else:
        prompt = f"[INST] {full_user_prompt} [/INST]"

    # No need to add an assistant token here, the format implies assistant response follows [/INST]
    return prompt


def format_prompt(formatter_hint: str, messages: List[Dict[str, Any]]) -> str:
    """
    Selects the appropriate prompt formatter based on the formatter_hint and formats
    the message history into a single string for the LLM.

    The selection is case-insensitive.
    If no specific format is found, it defaults to ChatML.

    :param formatter_hint: The hint for which formatter to use (e.g., 'llama3', 'mistral', 'chatml', 'alpaca', 'phi3').
    :type formatter_hint: str
    :param messages: A list of message dictionaries, each with a 'role' and 'content'.
    :type messages: List[Dict[str, Any]]
    :return: A single, correctly formatted prompt string.
    :rtype: str
    """
    hint_lower = ""
    if formatter_hint:
        hint_lower = formatter_hint.lower()

    if not messages:
        logger.warning(
            "format_prompt called with empty messages list. Returning empty prompt."
        )
        if "llama3" in hint_lower:
            return "<|begin_of_text|><|start_header_id|>assistant<|end_header_id|>\n\n"
        if (
            "chatml" in hint_lower
            or "mistral" in hint_lower
            or "qwen" in hint_lower
            or "mixtral" in hint_lower
        ):
            return "<|im_start|>assistant\n"
        if "alpaca" in hint_lower or "vicuna" in hint_lower:
            return "ASSISTANT: "
        if "phi3" in hint_lower:
            return "<|assistant|>"
        if "codellama-instruct" in hint_lower:
            return "[INST]  [/INST]"
        return "<|im_start|>assistant\n"

    if "llama3" in hint_lower:
        logger.debug(f"Using Llama 3 prompt format based on hint: {formatter_hint}")
        return _format_llama3(messages)

    if "phi3" in hint_lower:
        logger.debug(f"Using Phi-3 prompt format based on hint: {formatter_hint}")
        return _format_phi3(messages)

    if "codellama-instruct" in hint_lower:
        logger.debug(
            f"Using CodeLlama Instruct prompt format based on hint: {formatter_hint}"
        )
        return _format_codellama_instruct(messages)

    if "alpaca" in hint_lower or "vicuna" in hint_lower:
        logger.debug(
            f"Using Alpaca/Vicuna style prompt format based on hint: {formatter_hint}"
        )
        return _format_alpaca_vicuna(messages)

    # ChatML is a common format for Mistral, Mixtral, Qwen, and others.
    # It's also our general fallback.
    if (
        "mistral" in hint_lower
        or "mixtral" in hint_lower
        or "qwen" in hint_lower
        or "chatml" in hint_lower
    ):
        logger.debug(f"Using ChatML prompt format based on hint: {formatter_hint}")
        return _format_chatml(messages)

    # Fallback for completely unknown hints or if hint_lower was empty
    logger.warning(
        f"No specific prompt format matched for hint '{formatter_hint}'. "
        f"Using generic ChatML as a fallback. Ensure this is appropriate for the target model."
    )
    return _format_chatml(messages)
