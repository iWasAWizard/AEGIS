"""
Runtime test for a loopback graph using no_op.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig


def main():
    config = AgentGraphConfig(
        state_type=dict,
        entrypoint="start",
        condition_node=None,
        condition_map=None,
        edges=[
            ("start", "repeat"),
            ("repeat", "repeat"),  # loopback
            ("repeat", "end"),
        ],
        nodes=[
            NodeConfig(id="start", tool="no_op"),
            NodeConfig(id="repeat", tool="no_op"),
            NodeConfig(id="end", tool="no_op"),
        ],
    )

    test_input = {"dummy": "ok"}

    graph = AgentGraph(config)
    result = graph.run(test_input)
    print("=== LOOPBACK RUNTIME RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
