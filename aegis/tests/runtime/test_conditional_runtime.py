"""
Runtime test for AgentGraph with conditional routing using `next_step`.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig

# Define the graph config
config = AgentGraphConfig(
    state_type=dict,
    entrypoint="router",
    condition_node="router",
    condition_map={"echo": "echo", "noop": "noop"},
    edges=[],
    nodes=[
        NodeConfig(
            id="router",
            tool=None,  # Just a routing point
        ),
        NodeConfig(
            id="echo",
            tool="echo_input",
        ),
        NodeConfig(
            id="noop",
            tool="no_op",
        ),
    ],
)

# Input: use 'echo' or 'noop' to test routing
test_input = {
    "next_step": "echo",
    "payload": {"message": "This is a conditional test"},
    "dummy": "ignored",
}

# Run the graph
graph = AgentGraph(config)
result = graph.run(test_input)

print("=== CONDITIONAL RUNTIME RESULT ===")
print(result)
