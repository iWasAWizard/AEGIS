"""Encapsulates prompt construction for different agent use cases, like reflection and planning."""


def format_prompt(prompt: str) -> list:
    """
    format_prompt.

    :param prompt: Prompt to be formatted.
    :type prompt: str
    :return: Description of return value.
    :rtype: type
    """
    return [{"role": "user", "content": prompt}]
