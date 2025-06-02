"""
Graph composition runtime test.

Part 1: Simulates a chain of tools like a composed subgraph.
Part 2: Uses a tool function that runs its own internal AgentGraph.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig
from aegis.registry import register_tool
from pydantic import BaseModel, Field
import asyncio


# -------- Simulated subgraph via chained steps --------


def build_step_chain_graph():
    return AgentGraphConfig(
        state_type=dict,
        entrypoint="entry",
        condition_node=None,
        condition_map=None,
        edges=[
            ("entry", "phase_one"),
            ("phase_one", "phase_two"),
            ("phase_two", "end"),
        ],
        nodes=[
            NodeConfig(id="entry", tool="no_op"),
            NodeConfig(id="phase_one", tool="no_op"),
            NodeConfig(id="phase_two", tool="no_op"),
            NodeConfig(id="end", tool="echo_input"),
        ],
    )


# -------- Nested graph tool as callable --------


class SubgraphInput(BaseModel):
    payload: dict = Field(..., description="Initial input to the subgraph")


@register_tool(
    name="run_subgraph",
    input_model=SubgraphInput,
    description="Calls a nested graph internally and returns the result",
    tags=["test", "dev"],
    category="wrapper",
    safe_mode=True,
)
def run_subgraph(input_data: SubgraphInput) -> dict:
    sub_config = build_step_chain_graph()
    sub_graph = AgentGraph(sub_config)
    return asyncio.run(sub_graph.run(input_data.payload))


def main():
    print("=== SIMULATED SUBGRAPH TEST ===")
    chain_config = build_step_chain_graph()
    chain_graph = AgentGraph(chain_config)

    input_data = {"payload": {"note": "Simulated step chain test"}}

    result = chain_graph.run(input_data)
    print(result)

    print("\n=== NESTED GRAPH TOOL TEST ===")
    nested_config = AgentGraphConfig(
        state_type=dict,
        entrypoint="delegate",
        condition_node=None,
        condition_map=None,
        edges=[],
        nodes=[NodeConfig(id="delegate", tool="run_subgraph")],
    )

    nested_graph = AgentGraph(nested_config)
    nested_result = nested_graph.run(input_data)
    print(nested_result)


if __name__ == "__main__":
    main()
