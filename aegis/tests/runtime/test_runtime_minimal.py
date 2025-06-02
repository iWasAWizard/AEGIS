"""
Minimal runtime test for AgentGraph using echo_input only.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig


def main():
    config = AgentGraphConfig(
        state_type=dict,
        entrypoint="echo",
        condition_node=None,
        condition_map=None,
        edges=[],
        nodes=[
            NodeConfig(
                id="echo",
                tool="echo_input",
            )
        ],
    )

    test_input = {"payload": {"message": "Hello from minimal runtime test!"}}

    graph = AgentGraph(config)
    result = graph.run(test_input)
    print("=== MINIMAL RUNTIME RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
