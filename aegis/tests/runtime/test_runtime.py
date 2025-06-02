"""
Runtime test for minimal AgentGraph using the echo_input tool.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig

# Dummy config using only the echo_input tool
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

# Create a test input payload
test_input = {"payload": {"message": "Hello from runtime test!"}}

# Construct and run the graph
graph = AgentGraph(config)
result = graph.run(test_input)

print("=== RUNTIME TEST RESULT ===")
print(result)
