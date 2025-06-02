from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig
from aegis.agents.task_state import TaskState


def test_graph_compilation():
    config = AgentGraphConfig(
        state_type=TaskState,
        entrypoint="reflect",
        edges=[("reflect", "execute")],
        nodes=[
            NodeConfig(id="reflect", tool="reflect"),
            NodeConfig(id="execute", tool="execute"),
            NodeConfig(id="summarize", tool="summarize"),
        ],
        condition_node="execute",
        condition_map={"success": "summarize", "error": "reflect"},
    )
    graph = AgentGraph(config).build_graph()
    assert graph is not None
