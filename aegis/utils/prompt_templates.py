"""Defines templates for formatting multi-turn LLM messages, allowing compatibility with various LLM backends."""

from typing import List, Literal

from pydantic import BaseModel


class Message(BaseModel):
    """
    Message class.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class ChatTemplate:
    """
    ChatTemplate class.
    """

    def __init__(self, model_name: str):
        """
        __init__.
        :param model_name: Description of model_name
        :type model_name: Any
        :return: Description of return value
        :rtype: Any
        """
        self.model_name = model_name.lower()

    def format(self, messages: List[Message]) -> str:
        """
        format.
        :param messages: Description of messages
        :type messages: Any
        :return: Description of return value
        :rtype: Any
        """
        if "deephermes" in self.model_name or "chatml" in self.model_name:
            return self._format_chatml(messages)
        raise ValueError(f"No known prompt template for: {self.model_name}")

    @staticmethod
    def _format_chatml(messages: List[Message]) -> str:
        """
        _format_chatml.
        :param messages: Description of messages
        :type messages: Any
        :return: Description of return value
        :rtype: Any
        """
        formatted = ""
        for msg in messages:
            formatted += f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted
