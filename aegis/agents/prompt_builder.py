# aegis/agents/prompt_builder.py
"""
A dedicated builder for constructing the agent's planning prompts.
"""
import json
from typing import List, Dict, Any, Optional

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover
    tiktoken = None  # fallback below

from pydantic import BaseModel

from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.providers.base import BackendProvider
from aegis.registry import TOOL_REGISTRY, ToolEntry
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Human-readable signatures for meta-tools handled directly in execute_tool
_META_TOOL_SCHEMAS = [
    "- finish(final_summary: str (optional), truncate_history: bool (optional))",
    "- revise_goal(new_goal: str, reason: str (optional))",
    "- advance_to_next_sub_goal()",
    "- insert_sub_goals(index: int (optional), items: List[str])",
    "- remove_sub_goals(indices: List[int])",
    "- reorder_sub_goals(order: List[int])",
    "- set_current_sub_goal(index: int)",
]


class PromptBuilder:
    """Builds planner prompts and handles history compression.

    The constructor accepts the current TaskState, a list of tool names the
    planner may consider, and the active provider (unused here but kept for
    compatibility with existing call sites).
    """

    def __init__(
        self,
        state: TaskState,
        tool_names: List[str],
        provider: Optional[BackendProvider] = None,
    ) -> None:
        self.state = state
        self.tool_names = tool_names
        self.provider = provider

    def _encoding(self):
        if tiktoken is None:
            return None
        # default to cl100k_base which covers most chat models
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Rudimentary token count for chat messages."""
        enc = self._encoding()
        if enc is None:
            # crude fallback: ~4 chars per token
            text = "".join(m.get("content", "") for m in messages)
            return max(1, len(text) // 4)
        total = 0
        for m in messages:
            total += len(enc.encode(m.get("content", "")))
        return total

    def _field_type_str(self, field) -> str:
        # pydantic v2: field.annotation may be informative; fall back to type name
        try:
            ann = getattr(field, "annotation", None) or getattr(
                field, "outer_type_", None
            )
            if ann is None:
                return "Any"
            return (
                getattr(getattr(ann, "__name__", None), "strip", lambda: ann)()
                if isinstance(ann, str)
                else getattr(ann, "__name__", "Any")
            )
        except Exception:
            return "Any"

    def _get_tool_schemas(self) -> List[str]:
        """Return human-readable tool signatures for the allowed tools."""
        sigs: List[str] = []
        for tool_name in self.tool_names:
            try:
                entry: ToolEntry = TOOL_REGISTRY[tool_name]
            except Exception:
                logger.warning(f"Unknown tool '{tool_name}' in allowlist; skipping.")
                continue
            # derive description from function docstring if available
            try:
                desc = (entry.func.__doc__ or "").strip().splitlines()[0]
            except Exception:
                desc = ""
            # build arg signature from pydantic model
            parts: List[str] = []
            try:
                fields = getattr(entry.input_model, "model_fields", {})
                for name, fld in fields.items():
                    typ = self._field_type_str(fld)
                    optional = (
                        "" if getattr(fld, "is_required", False) else " (optional)"
                    )
                    parts.append(f"{name}: {typ}{optional}")
            except Exception as e:
                logger.warning(f"Could not inspect args for tool '{tool_name}': {e}")
            args_sig = ", ".join(parts)
            if desc:
                sigs.append(f"- {tool_name}({args_sig}): {desc}")
            else:
                sigs.append(f"- {tool_name}({args_sig})")
        return sigs

    def build_messages(self) -> List[Dict[str, str]]:
        """Construct planner messages including tool schemas and history compression."""
        s = self.state
        sys_lines: List[str] = []
        sys_lines.append(
            "You are an autonomous systems operator. Decide the next best tool to advance the task."
        )
        sys_lines.append(
            "Return a valid JSON object for the plan as specified by the response schema."
        )
        # available tools
        sigs = self._get_tool_schemas()
        if sigs:
            sys_lines.append("Available tools:")
            sys_lines.extend(sigs)

        # Also expose meta-tools that are not part of TOOL_REGISTRY
        try:
            sys_lines.extend(_META_TOOL_SCHEMAS)
        except Exception:
            pass

        system_msg = {"role": "system", "content": "\n".join(sys_lines)}

        user_lines: List[str] = []
        user_lines.append(f"Task: {s.task_prompt}")
        if getattr(s, "sub_goals", None):
            idx = getattr(s, "current_sub_goal_index", 0) or 0
            if 0 <= idx < len(s.sub_goals):
                user_lines.append(f"Current sub-goal: {s.sub_goals[idx]}")

        user_msg = {"role": "user", "content": "\n".join(user_lines)}

        # convert history entries to chat turns
        history_messages: List[Dict[str, str]] = []
        for h in s.history[
            -8:
        ]:  # keep last N entries raw; older ones summarized below if needed
            try:
                history_messages.append(
                    {"role": "assistant", "content": json.dumps(h.plan.model_dump())}
                )
                history_messages.append({"role": "tool", "content": h.observation})
            except Exception:
                continue

        full_messages = [system_msg, user_msg] + history_messages

        # compress if we exceed context budget
        max_ctx = getattr(s.runtime, "max_context_length", None) or 8192
        budget = int(max_ctx * 0.8)  # leave headroom for model output
        tok = self._count_tokens(full_messages)
        if tok <= budget:
            return full_messages

        # summarize older history beyond last N entries
        keep_n = 3
        history_to_keep = (
            s.history[-keep_n:] if len(s.history) >= keep_n else s.history[:]
        )
        older = s.history[:-keep_n] if len(s.history) > keep_n else []
        summary = (
            f"Summary of earlier steps ({len(older)} entries) omitted for brevity."
        )
        messages = [system_msg, user_msg]
        compressed_history_messages = [{"role": "assistant", "content": summary}]
        for entry in history_to_keep:
            try:
                compressed_history_messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(entry.plan.model_dump()),
                    }
                )
                compressed_history_messages.append(
                    {"role": "tool", "content": entry.observation}
                )
            except Exception:
                continue
        return messages + compressed_history_messages
