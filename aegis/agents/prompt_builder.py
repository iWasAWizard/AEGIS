# aegis/agents/prompt_builder.py
"""
A dedicated builder for constructing the agent's planning prompts.
"""
import json
from typing import List, Dict, Any

import tiktoken
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.providers.base import BackendProvider
from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptBuilder:
    """Encapsulates the logic for building the planning prompt."""

    def __init__(
        self, state: TaskState, relevant_tools: List[str], provider: BackendProvider
    ):
        self.state = state
        self.relevant_tools = relevant_tools
        self.provider = provider

    def _get_tool_schemas(self) -> str:
        """Gets formatted schema descriptions for a specific list of tools."""
        tool_signatures: List[str] = []

        for tool_name in sorted(self.relevant_tools):
            if tool_name not in TOOL_REGISTRY:
                continue
            tool_entry = TOOL_REGISTRY[tool_name]

            try:
                schema = tool_entry.input_model.model_json_schema()
                properties = schema.get("properties", {})
                required_args = set(schema.get("required", []))
                arg_parts = []
                for name, details in properties.items():
                    arg_type = details.get("type", "any")
                    part = f"{name}: {arg_type}"
                    if name not in required_args:
                        part += " (optional)"
                    arg_parts.append(part)
                args_signature = ", ".join(arg_parts)
                full_signature = (
                    f"- {tool_name}({args_signature}): {tool_entry.description}"
                )
                tool_signatures.append(full_signature)
            except Exception as e:
                logger.warning(
                    f"Could not generate signature for tool '{tool_name}': {e}"
                )

        finish_desc = "Call this tool ONLY when the user's entire request has been fully completed or is impossible to complete."
        tool_signatures.append(
            f"- finish(reason: string, status: string): {finish_desc}"
        )
        return "\n".join(tool_signatures)

    def _get_sub_goal_context(self) -> str:
        """Formats the sub-goal list for inclusion in the prompt."""
        if not self.state.sub_goals:
            return ""

        formatted_goals = []
        for i, goal in enumerate(self.state.sub_goals):
            if i == self.state.current_sub_goal_index:
                formatted_goals.append(f"  - **{i + 1}. {goal} (CURRENT FOCUS)**")
            else:
                formatted_goals.append(f"  - {i + 1}. {goal}")

        return f"""
        ## High-Level Plan
        You are currently working on a step in a larger plan. Focus only on the current sub-goal.

        {"\n".join(formatted_goals)}
        """

    async def _summarize_history(self, history_to_summarize: List[HistoryEntry]) -> str:
        """Uses an LLM call to summarize a portion of the agent's history."""
        logger.info(f"Summarizing {len(history_to_summarize)} oldest history entries.")
        history_str = "\n".join(
            [
                f"Step {i+1}: Thought: {entry.plan.thought}, Action: {entry.plan.tool_name}, Observation: {entry.observation}"
                for i, entry in enumerate(history_to_summarize)
            ]
        )
        prompt = (
            "You are a summarization engine. Condense the following agent execution history into a concise, one-paragraph summary. "
            "Focus on the key outcomes and conclusions, not the step-by-step process.\n\n"
            f"## History to Summarize\n{history_str}\n\n"
            "## Summary Paragraph"
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            summary = await self.provider.get_completion(
                messages, self.state.runtime, raw_response=False
            )
            return f"The following is a summary of earlier work that has already been completed: {summary}"
        except Exception as e:
            logger.error(f"Failed to summarize history: {e}")
            return "History summarization failed. Proceeding with truncated history."

    def _count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimates the token count of a list of messages."""
        try:
            # Use a common model for estimation, as exactness isn't critical
            enc = tiktoken.encoding_for_model("gpt-4")
            text_content = " ".join(
                str(msg.get("content", "")) for msg in messages if msg
            )
            return len(enc.encode(text_content))
        except Exception:
            # Fallback if tiktoken fails
            return sum(len(str(msg.get("content", ""))) // 4 for msg in messages if msg)

    async def build(self) -> List[Dict[str, Any]]:
        """Constructs the full message history, applying context compression if needed."""
        sub_goal_context = self._get_sub_goal_context()

        system_prompt = f"""You are an autonomous agent..."""  # Omitted for brevity

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.append(
            {"role": "user", "content": f"Here is my overall request: {self.state.task_prompt}"}
        )

        history_messages = []
        for entry in self.state.history:
            history_messages.append(
                {"role": "assistant", "content": json.dumps(entry.plan.model_dump())}
            )
            history_messages.append({"role": "tool", "content": entry.observation})

        full_messages = messages + history_messages
        token_count = self._count_tokens(full_messages)
        max_context = self.state.runtime.max_context_length or 4096

        if token_count > max_context * 0.8:
            logger.warning(
                f"Token count ({token_count}) exceeds 80% of max context ({max_context}). Compressing history."
            )
            # Find midpoint to summarize the first half of the history
            split_point = len(self.state.history) // 2
            history_to_summarize = self.state.history[:split_point]
            history_to_keep = self.state.history[split_point:]

            summary = await self._summarize_history(history_to_summarize)
            compressed_history_messages = [
                {"role": "assistant", "content": summary}
            ]
            for entry in history_to_keep:
                compressed_history_messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(entry.plan.model_dump()),
                    }
                )
                compressed_history_messages.append(
                    {"role": "tool", "content": entry.observation}
                )
            return messages + compressed_history_messages
        else:
            return full_messages