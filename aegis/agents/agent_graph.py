# aegis/agents/agent_graph.py
"""
Constructs and compiles a LangGraph StateGraph from an AgentGraphConfig.

This class takes a declarative configuration and translates it into an
executable LangGraph object, wiring up the nodes, edges, and conditional
logic required for the agent to run.
"""
from functools import partial

from langgraph.graph import StateGraph

from aegis.agents.node_registry import AGENT_NODE_REGISTRY
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentGraph:
    """A factory for creating a compiled LangGraph StateGraph from a configuration."""

    def __init__(self, config: AgentGraphConfig):
        """Initializes the AgentGraph builder with a given configuration.

        :param config: The configuration object defining the graph structure.
        :type config: AgentGraphConfig
        :raises TypeError: If the provided config is not an AgentGraphConfig instance.
        """
        if not isinstance(config, AgentGraphConfig):
            raise TypeError("AgentGraph expects a processed AgentGraphConfig object.")
        self.config = config

    def build_graph(self) -> StateGraph:
        """Builds and compiles the StateGraph based on the provided configuration.

        :return: A compiled, executable LangGraph StateGraph.
        :rtype: StateGraph
        """
        state_schema = self.config.state_type
        if not hasattr(state_schema, "model_validate"):
            raise TypeError(
                f"The state_type '{state_schema.__name__}' must be a Pydantic model."
            )

        logger.info(f"Building agent graph with state: {state_schema.__name__}")
        builder = StateGraph(state_schema)

        # Add all defined nodes to the graph builder
        for node_config in self.config.nodes:
            if node_config.tool not in AGENT_NODE_REGISTRY:
                raise ValueError(
                    f"Node function '{node_config.tool}' not found in AGENT_NODE_REGISTRY."
                )

            node_func = AGENT_NODE_REGISTRY[node_config.tool]
            node_to_add = node_func

            # --- DEPENDENCY INJECTION ---
            # If a node needs a dependency (like the LLM), bind it here.
            if node_config.tool == "reflect_and_plan":
                node_to_add = partial(node_func, llm_query_func=llm_query)

            builder.add_node(node_config.id, node_to_add)
            logger.debug(
                f"Added node '{node_config.id}' with function '{node_config.tool}'"
            )

        # Set the entry point
        builder.set_entry_point(self.config.entrypoint)
        logger.debug(f"Set entry point to '{self.config.entrypoint}'")

        # Add all unconditional edges
        for src, dst in self.config.edges:
            builder.add_edge(src, dst)
            logger.debug(f"Added edge: {src} -> {dst}")

        # Add conditional routing logic if it's defined
        if self.config.condition_node and self.config.condition_map:
            if self.config.condition_node not in [n.id for n in self.config.nodes]:
                raise ValueError(
                    f"Conditional node '{self.config.condition_node}' is not defined in the nodes list."
                )

            # The condition_node's function must be passed directly to be called by the graph.
            builder.add_conditional_edges(
                self.config.condition_node,
                AGENT_NODE_REGISTRY[self.config.condition_node],
                self.config.condition_map,
            )
            logger.debug(
                f"Added conditional edge from '{self.config.condition_node}' with map: {self.config.condition_map}"
            )

        logger.info("Graph construction complete. Compiling...")
        return builder.compile()
