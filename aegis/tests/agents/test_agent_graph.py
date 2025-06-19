# aegis/tests/agents/test_agent_graph.py
"""
Unit tests for the AgentGraph builder.
"""
from unittest.mock import MagicMock

import pytest
from langgraph.pregel import Pregel

from aegis.agents.agent_graph import AgentGraph
from aegis.exceptions import ConfigurationError
from aegis.schemas.agent import AgentGraphConfig
from aegis.schemas.config import NodeConfig


@pytest.fixture
def valid_graph_config() -> AgentGraphConfig:
    """Provides a valid AgentGraphConfig object for testing."""
    return AgentGraphConfig(
        state_type=MagicMock(),
        entrypoint="plan",
        nodes=[
            NodeConfig(id="plan", tool="reflect_and_plan"),
            NodeConfig(id="execute", tool="execute_tool"),
            NodeConfig(id="check_termination", tool="check_termination"),
        ],
        edges=[("plan", "execute")],
        condition_node="check_termination",
        condition_map={"continue": "plan", "end": "__end__"},
    )


def test_build_graph_success(valid_graph_config):
    """Verify that a valid config builds a Pregel graph with correct structure."""
    agent_graph_builder = AgentGraph(valid_graph_config)
    compiled_graph = agent_graph_builder.build_graph()

    assert isinstance(compiled_graph, Pregel)

    # Check that nodes were added
    assert "plan" in compiled_graph.nodes
    assert "execute" in compiled_graph.nodes
    assert "check_termination" in compiled_graph.nodes

    # Check that edges were added
    assert compiled_graph.edges == {("plan", "execute")}

    # Check that conditional branches were added
    assert "check_termination" in compiled_graph.branches
    branch = compiled_graph.branches["check_termination"]
    assert len(branch.ends) == 2
    assert branch.ends["continue"] == "plan"
    assert branch.ends["end"] == "__end__"


@pytest.mark.parametrize(
    "invalid_field, invalid_value, error_msg",
    [
        ("entrypoint", "non_existent_node", "Invalid graph configuration"),
        ("edges", [("plan", "non_existent_node")], "Invalid graph configuration"),
        (
            "condition_node",
            "non_existent_node",
            "Conditional node 'non_existent_node' is not defined",
        ),
    ],
)
def test_build_graph_invalid_config(
    valid_graph_config, invalid_field, invalid_value, error_msg
):
    """Verify that an invalid configuration raises a ConfigurationError."""
    # Create a mutable copy of the config to modify
    invalid_config_dict = valid_graph_config.model_dump()
    invalid_config_dict[invalid_field] = invalid_value

    invalid_config = AgentGraphConfig(**invalid_config_dict)

    with pytest.raises(ConfigurationError, match=error_msg):
        AgentGraph(invalid_config).build_graph()
