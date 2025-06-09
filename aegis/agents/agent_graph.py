# aegis/agents/agent_graph.py
"""
Constructs and compiles a LangGraph StateGraph from an AgentGraphConfig.

This class takes a declarative configuration and translates it into an
executable LangGraph object, wiring up the nodes, edges, and conditional
logic required for the agent to run.
"""
from functools import partial

from langgraph.graph import StateGraph
from langgraph.pregel import Pregel

from aegis.exceptions import ConfigurationError
from aegis.schemas.agent import AgentGraphConfig
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger
from schemas.node_registry import AGENT_NODE_REGISTRY

logger = setup_logger(__name__)


class AgentGraph:
    """A factory for creating a compiled LangGraph StateGraph from a configuration."""

    def __init__(self, config: AgentGraphConfig):
        """Initializes the AgentGraph builder with a given configuration.

        :param config: The configuration object defining the graph structure.
        :type config: AgentGraphConfig
        :raises ConfigurationError: If the provided config is not an AgentGraphConfig instance.
        """
        logger.debug(f"Initializing AgentGraph with config: {config.model_dump_json(indent=2)}")
        if not isinstance(config, AgentGraphConfig):
            raise ConfigurationError("AgentGraph expects a processed AgentGraphConfig object.")
        self.config = config

    def build_graph(self) -> Pregel:
        """Builds and compiles the StateGraph based on the provided configuration.

        :return: A compiled, executable LangGraph Pregel object.
        :rtype: Pregel
        :raises ConfigurationError: If the graph configuration is invalid.
        """
        logger.info(f"Building agent graph with state: {self.config.state_type.__name__}")
        try:
            builder = StateGraph(self.config.state_type)

            for node_config in self.config.nodes:
                if node_config.tool not in AGENT_NODE_REGISTRY:
                    raise ValueError(f"Node function '{node_config.tool}' not found in AGENT_NODE_REGISTRY.")
                node_func = AGENT_NODE_REGISTRY[node_config.tool]

                # Bind dependencies like the LLM query function to the relevant nodes
                node_to_add = node_func
                if node_config.tool in ["reflect_and_plan", "remediate_plan"]:
                    node_to_add = partial(node_func, llm_query_func=llm_query)

                builder.add_node(node_config.id, node_to_add)
                logger.debug(f"Added node '{node_config.id}' with function '{node_config.tool}'")

            builder.set_entry_point(self.config.entrypoint)
            logger.debug(f"Set entry point to '{self.config.entrypoint}'")

            for src, dst in self.config.edges:
                builder.add_edge(src, dst)
                logger.debug(f"Added edge: {src} -> {dst}")

            if self.config.condition_node and self.config.condition_map:
                if self.config.condition_node not in [n.id for n in self.config.nodes]:
                    raise ValueError(f"Conditional node '{self.config.condition_node}' is not defined in nodes list.")

                # Resolve the function associated with the condition node
                condition_node_tool_name = next(n.tool for n in self.config.nodes if n.id == self.config.condition_node)
                condition_func = AGENT_NODE_REGISTRY[condition_node_tool_name]

                builder.add_conditional_edges(self.config.condition_node, condition_func, self.config.condition_map)
                logger.debug(
                    f"Added conditional edge from '{self.config.condition_node}' with map: {self.config.condition_map}")

            logger.info("Graph construction complete. Compiling...")
            compiled_graph = builder.compile()
            logger.info("Graph compiled successfully.")
            return compiled_graph

        except (TypeError, ValueError) as e:
            logger.exception(f"Failed to build agent graph due to configuration error: {e}")
            raise ConfigurationError(f"Invalid graph configuration: {e}") from e
