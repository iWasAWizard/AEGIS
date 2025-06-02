from langgraph.graph import StateGraph

from aegis.agents.node_registry import AGENT_NODE_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentGraph:
    """
    Represents the AgentGraph class.

    Use this class to define and manage the execution graph for agent workflows.
    """

    def __init__(self, config):
        """
        __init__.
        :param config: Description of config
        :type config: Any
        :return: Description of return value
        :rtype: Any
        """
        self.config = config

    def build_graph(self):
        """
        build_graph.
        :return: Description of return value
        :rtype: Any
        """
        logger.debug(
            f"Initializing StateGraph with state_type: {self.config.state_type}"
        )
        builder = StateGraph(self.config.state_type)
        for name in (
                {self.config.entrypoint}
                | {src for src, _ in self.config.edges}
                | {dst for _, dst in self.config.edges}
                | set(self.config.condition_map.values())
        ):
            builder.add_node(name, AGENT_NODE_REGISTRY[name])
        logger.debug(f"Setting entry point to: {self.config.entrypoint}")
        builder.set_entry_point(self.config.entrypoint)
        for edge in self.config.edges:
            logger.debug(f"Adding edge: {edge[0]} -> {edge[1]}")
            builder.add_edge(edge[0], edge[1])
        if self.config.condition_node and self.config.condition_map:
            logger.debug(f"Resolving condition_map: {self.config.condition_map}")

            def resolved_map(state: dict) -> str:
                """
                resolved_map.
                :param state: Description of state
                :type state: Any
                :return: Description of return value
                :rtype: Any
                """
                key = state.get("next_step")
                if key not in self.config.condition_map:
                    raise ValueError(f"Unknown routing key: {key}")
                return AGENT_NODE_REGISTRY[self.config.condition_map[key]]

            logger.debug(f"Resolved map: {resolved_map}")
            builder.add_conditional_edges(self.config.condition_node, resolved_map)
        if hasattr(self.config, "middleware") and self.config.middleware:
            logger.debug(f"Adding middleware: {self.config.middleware}")
        logger.debug("Setting finish point to summarize")
        builder.set_finish_point("summarize")
        compiled = builder.compile()
        logger.debug("Graph compilation complete")
        return compiled

    async def run(self, input_data):
        """
        run.
        :param input_data: Description of input_data
        :type input_data: Any
        :return: Description of return value
        :rtype: Any
        """
        logger.debug(f"Running graph with input data: {input_data}")
        graph = self.build_graph()
        result = await graph.ainvoke(input_data)
        logger.debug(f"Graph execution complete, result: {result}")
        return result
