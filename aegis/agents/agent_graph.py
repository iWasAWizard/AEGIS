# aegis/agents/agent_graph.py
"""
Constructs and compiles a LangGraph StateGraph from an AgentGraphConfig.
"""
from functools import partial
from typing import Callable  # Added Callable for type hinting

from langgraph.graph import StateGraph  # Ensured StateGraph is imported
from langgraph.pregel import Pregel

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.verification import route_after_verification  # Import this
from aegis.exceptions import ConfigurationError
from aegis.schemas.agent import AgentGraphConfig
from aegis.schemas.node_registry import AGENT_NODE_REGISTRY
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
# logger.info("Initializing aegis.agents.agent_graph module...") # Already in original


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

                node_to_add = node_func
                if node_config.tool in ["reflect_and_plan", "remediate_plan"]:
                    node_to_add = partial(node_func, llm_query_func=llm_query)

                builder.add_node(node_config.id, node_to_add)
                logger.debug(
                    f"Added node '{node_config.id}' with function '{node_config.tool}'"
                )

            builder.set_entry_point(self.config.entrypoint)
            logger.debug(f"Set entry point to '{self.config.entrypoint}'")

            for src, dst in self.config.edges:
                builder.add_edge(src, dst)
                logger.debug(f"Added edge: {src} -> {dst}")

            if self.config.condition_node and self.config.condition_map:
                source_node_id_for_conditional = self.config.condition_node

                decision_function_for_routing: Callable
                # Explicitly choose the routing function based on the source node ID from config
                if (
                    source_node_id_for_conditional == "execute"
                ):  # This is for default.yaml
                    decision_function_for_routing = check_termination
                    logger.debug(
                        f"Using 'check_termination' as decision function for conditional edge from '{source_node_id_for_conditional}'."
                    )
                elif (
                    source_node_id_for_conditional == "verify"
                ):  # This is for verified_flow.yaml
                    decision_function_for_routing = route_after_verification
                    logger.debug(
                        f"Using 'route_after_verification' as decision function for conditional edge from '{source_node_id_for_conditional}'."
                    )
                else:
                    # This generic fallback might be hit if you create new presets
                    # and the condition_node is a node whose registered tool IS the decider function.
                    cond_node_config = next(
                        (
                            n
                            for n in self.config.nodes
                            if n.id == source_node_id_for_conditional
                        ),
                        None,
                    )
                    if (
                        cond_node_config
                        and cond_node_config.tool in AGENT_NODE_REGISTRY
                    ):
                        decision_function_for_routing = AGENT_NODE_REGISTRY[
                            cond_node_config.tool
                        ]
                        logger.debug(
                            f"Using tool '{cond_node_config.tool}' from node '{source_node_id_for_conditional}' as decision function."
                        )
                    else:
                        raise ConfigurationError(
                            f"Could not determine decision function for conditional node '{source_node_id_for_conditional}'. "
                            f"Ensure it's correctly defined in preset or handled explicitly here."
                        )

                builder.add_conditional_edges(
                    source_node_id_for_conditional,
                    decision_function_for_routing,
                    self.config.condition_map,
                )
                logger.debug(
                    f"Added conditional edge from '{source_node_id_for_conditional}' with map: {self.config.condition_map} using function "
                    f"'{decision_function_for_routing.__name__}'"
                )

            logger.info("Graph construction complete. Compiling...")
            compiled_graph = builder.compile()
            logger.info("Graph compiled successfully.")
            return compiled_graph

        except (
            TypeError,
            ValueError,
            ConfigurationError,
        ) as e:  # Added ConfigurationError
            logger.exception(
                f"Failed to build agent graph due to configuration error: {e}"
            )
            raise ConfigurationError(f"Invalid graph configuration: {e}") from e
