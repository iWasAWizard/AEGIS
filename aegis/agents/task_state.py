"""Defines the TaskState data structure for agent task execution and runtime coordination."""

from time import time
from typing import List, Dict, Optional, Any, Callable, Awaitable

from pydantic import BaseModel, Field, PrivateAttr

from aegis.utils.logger import setup_logger
from aegis.schemas.runtime_execution_config import RuntimeExecutionConfig

logger = setup_logger(__name__)


class TaskState(BaseModel):
    """
    Represents the TaskState class.

    Tracks runtime state for a task, including prompt, execution results, and conversation history.
    """

    task_id: str
    task_prompt: str
    steps_taken: int = Field(0)
    plan: List[str] = Field(default_factory=list)
    results: List[str] = Field(default_factory=list)
    analysis: List[str] = Field(default_factory=list)
    tool_name: Optional[str] = Field(default=None)
    safe_mode: bool = Field(default=True)
    summary: Optional[str] = Field(None)
    plan_step: Optional[Dict[str, Any]] = Field(default_factory=dict)
    next_step: Optional[str] = None
    tool_request: Optional[Any] = Field(default=None)
    shell_execute: Optional[Callable] = Field(None)
    sensor_outputs: Dict[str, List[Any]] = Field(default_factory=dict)
    steps_output: Dict[str, Any] = Field(default_factory=dict)
    runtime: RuntimeExecutionConfig
    _start_time: Optional[float] = PrivateAttr(default_factory=time)
    _profile_name: Optional[str] = PrivateAttr(default="default")
    _llm_query_fn: Optional[Callable[[str], str]] = PrivateAttr(default=None)

    @property
    def llm_query(self) -> Callable[[str], Awaitable[str]]:
        if self._llm_query_fn is None:
            raise RuntimeError("LLM query function is not attached.")
        return self._llm_query_fn

    def log_state(self):
        """
        log_state.
        :return: Description of return value
        :rtype: Any
        """
        logger.info(f"[TaskState] Iteration {self.steps_taken}")
        if self.plan:
            logger.debug(f"[TaskState] Current plan: {self.plan}")
        if self.results:
            logger.debug(f"[TaskState] Results so far: {self.results}")
        if self.analysis:
            logger.debug(f"[TaskState] Analysis: {self.analysis}")
        if self.summary:
            logger.info(f"[TaskState] Final Summary: {self.summary}")


def attach_runtime(state: TaskState, llm_query_fn):
    """
    attach_runtime.
    :param state: Description of state
    :param llm_query_fn: Description of llm_query_fn
    :type state: Any
    :type llm_query_fn: Any
    :return: Description of return value
    :rtype: Any
    """
    state._llm_query_fn = llm_query_fn
    return state
