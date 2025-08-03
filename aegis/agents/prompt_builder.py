# aegis/agents/prompt_builder.py
"""
A dedicated builder for constructing the agent's planning prompts.
"""
import json
from typing import List, Dict, Any

from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptBuilder:
    """Encapsulates the logic for building the planning prompt."""

    def __init__(self, state: TaskState, relevant_tools: List[str]):
        self.state = state
        self.relevant_tools = relevant_tools

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

    def build(self) -> List[Dict[str, Any]]:
        """Constructs the full message history for the LLM planner."""
        sub_goal_context = self._get_sub_goal_context()

        system_prompt = f"""You are an autonomous agent. Your task is to achieve the user's goal by thinking step-by-step and selecting one tool at a time.
        {sub_goal_context}
        ## Instructions
        1.  **Analyze Goal & History:** Review the user's goal, the current sub-goal, and the history of actions taken so far.
        2.  **Plan ONE Step:** Decide on the single next action to advance the current sub-goal. Your response must be a single tool call in JSON format.
        3.  **Advance Plan:** When you have fully completed the current sub-goal, you MUST call the `advance_to_next_sub_goal` tool.
        4.  **Self-Correction:** If you realize the original goal is flawed or impossible, use the `revise_goal` tool to change it.

        ## Task Completion
        The `finish` tool is MANDATORY for completing the entire task. Call it only when all sub-goals are complete.
        - DO NOT provide a final summary. Your final output MUST be a JSON object calling the `finish` tool.

        ## Response Format Example
        ```json
        {{
        "thought": "I need to write the user's requested script to a file. This will address the current sub-goal.",
        "tool_name": "write_to_file",
        "tool_args": {{
            "path": "script.py",
            "content": "print('hello')"
        }}
        }}

        ## Available Tools for this step

        {self._get_tool_schemas()}
        """

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.append(
            {"role": "user", "content": f"Here is my overall request: {self.state.task_prompt}"}
        )

        for entry in self.state.history:
            messages.append(
                {"role": "assistant", "content": json.dumps(entry.plan.model_dump())}
            )
            messages.append({"role": "tool", "content": entry.observation})

        return messages