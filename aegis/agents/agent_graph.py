# aegis/agents/agent_graph.py
"""
Constructs and compiles a LangGraph StateGraph from an AgentGraphConfig.
"""
from functools import partial
from typing import Callable

from langgraph.graph import StateGraph
from langgraph.pregel import Pregel

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.verification import route_after_verification
from aegis.exceptions import ConfigurationError
from aegis.schemas.agent import AgentGraphConfig
from aegis.schemas.node_registry import AGENT_NODE_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentGraph:
    """A factory for creating a compiled LangGraph StateGraph from a configuration."""

    def __init__(self, config: AgentGraphConfig):
        """Initializes the AgentGraph builder with a given configuration.

        :param config: The configuration object defining the graph structure.
        :type config: AgentGraphConfig
        :raises ConfigurationError: If the provided config is not an AgentGraphConfig instance.
        """
        logger.debug(f"Initializing AgentGraph with config: {repr(config)}")
        if not isinstance(config, AgentGraphConfig):
            raise ConfigurationError(
                "AgentGraph expects a processed AgentGraphConfig object."
            )
        self.config = config

    def build_graph(self) -> Pregel:
        """Builds and compiles the StateGraph based on the provided configuration.

        :return: A compiled, executable LangGraph Pregel object.
        :rtype: Pregel
        :raises ConfigurationError: If the graph configuration is invalid.
        """
        logger.info(
            f"Building agent graph with state: {self.config.state_type.__name__}"
        )
        try:
            builder = StateGraph(self.config.state_type)

            for node_config in self.config.nodes:
                if node_config.tool not in AGENT_NODE_REGISTRY:
                    raise ConfigurationError(
                        f"Node function '{node_config.tool}' not found in AGENT_NODE_REGISTRY."
                    )
                node_func = AGENT_NODE_REGISTRY[node_config.tool]
                builder.add_node(node_config.id, node_func)
                logger.debug(
                    f"Added node '{node_config.id}' with function '{node_config.tool}'"
                )

            builder.set_entry_point(self.config.entrypoint)
            logger.debug(f"Set entry point to '{self.config.entrypoint}'")

            for src, dst in self.config.edges:
                builder.add_edge(src, dst)
                logger.debug(f"Added edge: {src} -> {dst}")

            if self.config.condition_node and self.config.condition_map:
                # The node that is used as the *source* for the conditional edge
                source_node_id_for_conditional = self.config.condition_node

                # The function that is called to get the routing *decision*
                # The logic inside this function determines which key from condition_map to use.
                # In our presets, the conditional routing decision logic is always in `check_termination`
                # for the basic flow, or `route_after_verification` for the advanced one.
                # We need to map the source node of the branch to the correct decision function.
                decision_function_for_routing: Callable

                if self.config.condition_node == "execute":
                    # In default.yaml, after 'execute', we call 'check_termination' to decide where to go.
                    decision_function_for_routing = check_termination
                elif self.config.condition_node == "verify":
                    # In verified_flow.yaml, after 'verify', we call 'route_after_verification'.
                    decision_function_for_routing = route_after_verification
                else:
                    # Fallback for other potential custom flows
                    decision_function_for_routing = AGENT_NODE_REGISTRY.get(
                        source_node_id_for_conditional, check_termination
                    )

                builder.add_conditional_edges(
                    source_node_id_for_conditional,
                    decision_function_for_routing,
                    self.config.condition_map,
                )
                logger.debug(
                    f"Added conditional edge from '{source_node_id_for_conditional}' "
                    f"with map: {self.config.condition_map}"
                )

            logger.info("Graph construction complete. Compiling...")
            compiled_graph = builder.compile(
                interrupt_before=self.config.interrupt_nodes
            )
            logger.info("Graph compiled successfully.")
            return compiled_graph

        except (
            TypeError,
            ValueError,
            ConfigurationError,
        ) as e:
            logger.exception(
                f"Failed to build agent graph due to configuration error: {e}"
            )
            raise ConfigurationError(f"Invalid graph configuration: {e}") from e
