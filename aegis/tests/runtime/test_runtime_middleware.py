"""
Runtime test with graph-wide middleware to modify state.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig
from aegis.utils.logger import setup_logger


logger = setup_logger(__name__)


def inject_visited_middleware(state: dict) -> dict:
    visited = state.visited
    current = state.step_id
    visited.append(current)
    state["visited"] = visited
    logger.debug(f"[middleware] Step visited: {current}")
    return state


def main():
    config = AgentGraphConfig(
        state_type=dict,
        entrypoint="echo",
        condition_node=None,
        condition_map=None,
        edges=[],
        nodes=[
            NodeConfig(id="echo", tool="echo_input"),
        ],
        middleware=[inject_visited_middleware],
    )

    test_input = {
        "step_id": "echo",
        "payload": {"note": "This graph modifies state via middleware."},
    }

    graph = AgentGraph(config)
    result = graph.run(test_input)
    print("=== MIDDLEWARE RUNTIME RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
