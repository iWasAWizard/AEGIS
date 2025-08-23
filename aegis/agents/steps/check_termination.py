# aegis/agents/steps/check_termination.py
"""
The termination and routing step for the agent graph.

This function acts as the main conditional router. It inspects the agent's
state after each tool execution to decide whether to continue the loop or
to terminate the task.
"""

import time
from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def check_termination(state: TaskState) -> str:
    """Determines if the agent should continue, interrupt, or end the task.

    This function acts as a conditional edge in the graph. It checks for
    a 'finish' tool call, an 'ask_human_for_input' call, or if the step
    limit has been reached.

    :param state: The current state of the agent's task.
    :type state: TaskState
    :return: A routing string: 'continue', 'interrupt', or 'end'.
    :rtype: str
    """
    logger.info("✅ Step: Check for Termination")
    logger.debug(
        f"Current state: steps_taken={state.steps_taken}, max_iterations={state.runtime.iterations}"
    )

    if not state.history:
        return "continue"

    last_tool_name = state.history[-1].plan.tool_name

    # Wall-clock guard (optional): end the task if the overall budget is exceeded.
    timeout = getattr(state.runtime, "wall_clock_timeout_s", None)
    if timeout:
        try:
            # Prefer an explicit task start timestamp if your state has one…
            started = getattr(state, "start_time", None)
            # …otherwise fall back to the first recorded step's start time.
            if started is None and state.history:
                started = getattr(state.history[0], "start_time", None)

            if started is not None and (time.time() - started) >= timeout:
                logger.warning(
                    f"Termination condition met: wall-clock timeout {timeout}s exceeded."
                )
                return "end"
        except Exception:
            # Guard must never crash routing—fail open and continue.
            pass

    # Degeneracy guard: end if the last 3 steps produced identical observations.
    try:
        k = 3
        if len(state.history) >= k:
            tail = state.history[-k:]
            obs = [getattr(h, "observation", None) for h in tail]
            if all(isinstance(o, str) for o in obs) and len(set(obs)) == 1:
                logger.warning(
                    "Termination condition met: degenerate loop "
                    f"(identical observations in last {k} steps)."
                )
                return "end"
    except Exception:
        # Guard must never crash routing—fail open and continue.
        pass

    # Interrupt when a preflight preview requested human approval
    try:
        if state.history:
            last_obs = getattr(state.history[-1], "observation", "") or ""
            if isinstance(last_obs, str) and last_obs.lstrip().startswith(
                "[APPROVAL REQUIRED]"
            ):
                logger.info(
                    "Interrupt condition met: approval required by policy preflight."
                )
                return "interrupt"
    except Exception:
        pass

    # Auto-finish when sub-goals are completed
    try:
        total = len(getattr(state, "sub_goals", []) or [])
        idx = int(getattr(state, "current_sub_goal_index", 0) or 0)
        if total == 0 or idx >= total:
            logger.info("Termination condition met: all sub-goals completed.")
            return "end"
    except Exception:
        # Never block termination routing on bookkeeping errors
        pass

    # Condition 1: Check if the last planned tool was 'finish'.
    if last_tool_name == "finish":
        logger.info("Termination condition met: 'finish' tool was called.")
        return "end"

    # Condition 2: Check if the last tool was a request for human input.
    if last_tool_name == "ask_human_for_input":
        logger.info("Interrupt condition met: 'ask_human_for_input' tool was called.")
        try:
            from aegis.utils.replay_logger import log_replay_event

            log_replay_event(state.task_id, "INTERRUPT_FOR_APPROVAL", {})
        except Exception:
            pass

        return "interrupt"

    # Condition 3: Check if the maximum number of steps has been reached.
    max_steps = state.runtime.iterations
    if max_steps is not None and state.steps_taken >= max_steps:
        logger.warning(f"Termination condition met: Max steps ({max_steps}) reached.")
        return "end"

    # If no termination conditions are met, continue the loop.
    logger.info("No termination condition met. Continuing to next planning step.")
    return "continue"
