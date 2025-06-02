"""
Conditional runtime test for AgentGraph using a router.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig


def main():
    config = AgentGraphConfig(
        state_type=dict,
        entrypoint="router",
        condition_node="router",
        condition_map={"echo": "echo", "noop": "noop"},
        edges=[],
        nodes=[
            NodeConfig(id="router", tool=None),
            NodeConfig(id="echo", tool="echo_input"),
            NodeConfig(id="noop", tool="no_op"),
        ],
    )

    test_input = {
        "next_step": "noop",  # Try 'echo' or 'noop'
        "payload": {"message": "Conditional test"},
        "dummy": "ignored",
    }

    graph = AgentGraph(config)
    result = graph.run(test_input)
    print("=== CONDITIONAL RUNTIME RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
