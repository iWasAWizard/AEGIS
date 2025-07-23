# aegis/evaluation/eval_runner.py
"""
Core logic for running evaluations against the AEGIS agent using LangFuse datasets.
"""
import asyncio
from typing import List, Dict, Any

from langfuse import Langfuse
from langfuse.model import CreateScore
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentEvaluator:
    """Orchestrates the process of running evaluations."""

    def __init__(self, dataset_name: str, judge_model_profile: str):
        self.dataset_name = dataset_name
        self.langfuse = Langfuse()
        self.dataset = self.langfuse.get_dataset(name=self.dataset_name)

        # For now, we assume the judge LLM is an OpenAI-compatible API.
        # This could point to vLLM or OpenAI itself.
        # A more advanced version could use the backend_loader.
        self.judge_llm = ChatOpenAI(model=judge_model_profile, temperature=0)
        logger.info(
            f"Evaluator initialized for dataset '{dataset_name}' with judge '{judge_model_profile}'"
        )

    async def _run_agent_for_item(self, item) -> Dict[str, Any]:
        """Runs the AEGIS agent for a single dataset item."""
        try:
            # Reconstruct a LaunchRequest from the dataset item
            # Assumes item.input is a dict that looks like a LaunchRequest
            payload = LaunchRequest.model_validate(item.input)

            preset_config: AgentConfig = load_agent_config(
                profile=payload.config if isinstance(payload.config, str) else "default"
            )
            runtime_config = preset_config.runtime
            if payload.execution:
                runtime_config = runtime_config.model_copy(
                    update=payload.execution.model_dump(exclude_unset=True)
                )

            initial_state = TaskState(
                task_id=item.id, task_prompt=payload.task.prompt, runtime=runtime_config
            )
            graph_structure = AgentGraphConfig(
                state_type=preset_config.state_type,
                entrypoint=preset_config.entrypoint,
                nodes=preset_config.nodes,
                edges=preset_config.edges,
                condition_node=preset_config.condition_node,
                condition_map=preset_config.condition_map,
                interrupt_nodes=preset_config.interrupt_nodes,
            )
            agent_graph = AgentGraph(graph_structure).build_graph()
            final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
            final_state = TaskState(**final_state_dict)

            return {
                "output": final_state.final_summary,
                "trace_id": item.link(self.langfuse, run_id=initial_state.task_id),
            }
        except Exception as e:
            logger.error(f"Agent run failed for dataset item {item.id}: {e}")
            return {"output": f"AGENT_EXECUTION_ERROR: {e}", "trace_id": None}

    async def evaluate_run(self, item, agent_output: str) -> CreateScore:
        """Uses an LLM-as-judge to evaluate the agent's output against the expected output."""
        system_prompt = (
            "You are a meticulous evaluator. Your task is to score an AI agent's performance. "
            "Compare the agent's actual output to the expected output. "
            "Respond with a single integer score from 1 to 5, where 1 is a complete failure and 5 is a perfect match. "
            "Provide a short rationale for your score in the next sentence."
        )
        user_prompt = (
            f"## Task Input\n{item.input['task']['prompt']}\n\n"
            f"## Expected Output\n```\n{item.expected_output}\n```\n\n"
            f"## Agent's Actual Output\n```\n{agent_output}\n```\n\n"
            f"## Score (1-5):"
        )

        llm_result: LLMResult = await self.judge_llm.agenerate(
            [[("system", system_prompt), ("user", user_prompt)]]
        )
        judge_response = llm_result.generations[0][0].text

        # Parse the score and rationale
        score_value = 1
        rationale = "Could not parse judge response."
        try:
            score_str = judge_response.strip().split()[0]
            if score_str.isdigit():
                score_value = int(score_str)
            rationale = " ".join(judge_response.strip().split()[1:])
        except Exception:
            pass

        logger.info(f"Item {item.id} scored: {score_value}/5. Rationale: {rationale}")
        return CreateScore(name="Correctness", value=score_value, comment=rationale)

    async def run_evaluations(self):
        """Runs the full evaluation suite for the dataset."""
        logger.info(f"Starting evaluation run on {len(self.dataset.items)} items.")
        for item in self.dataset.items:
            logger.info(f"--- Processing item {item.id} ---")
            run_result = await self._run_agent_for_item(item)
            agent_output = run_result["output"]
            trace_id = run_result["trace_id"]

            if trace_id:
                score = await self.evaluate_run(item, agent_output)
                self.langfuse.score(trace_id=trace_id, **score.model_dump())
                logger.info(f"Score for trace {trace_id} logged to LangFuse.")
            else:
                logger.warning(
                    f"Skipping scoring for item {item.id} due to execution failure."
                )
        logger.info("--- Evaluation run complete ---")


async def main(dataset_name: str, judge_model: str):
    """Main async entry point for the evaluation runner."""
    evaluator = AgentEvaluator(
        dataset_name=dataset_name, judge_model_profile=judge_model
    )
    await evaluator.run_evaluations()
