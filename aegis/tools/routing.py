from difflib import get_close_matches
from typing import Optional, List

from aegis.registry import TOOL_REGISTRY, ToolEntry
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_tool_for_task(
        task_description: str,
        threshold: float = 0.5,
        category: Optional[str] = None,
        required_tags: Optional[List[str]] = None,
        safe_only: bool = False,
        top_k: int = 1,
        return_all_matches: bool = False,
) -> Optional[ToolEntry] | List[ToolEntry]:
    """
    get_tool_for_task.
    :param task_description: Description of task_description
    :param threshold: Description of threshold
    :param category: Description of category
    :param required_tags: Description of required_tags
    :param safe_only: Description of safe_only
    :param top_k: Description of top_k
    :param return_all_matches: Description of return_all_matches
    :type task_description: Any
    :type threshold: Any
    :type category: Any
    :type required_tags: Any
    :type safe_only: Any
    :type top_k: Any
    :type return_all_matches: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug(
        f"Starting get_tool_for_task with: task_description={task_description},"
        f"                  category={category}"
        f"                  required_tags={required_tags}"
        f"                  safe_only={safe_only}"
    )
    candidates = []
    for tool in TOOL_REGISTRY.values():
        if category and tool.category != category:
            continue
        if safe_only and (not tool.safe_mode):
            continue
        if required_tags and (not all((tag in tool.tags for tag in required_tags))):
            continue
        metadata = [tool.name, tool.purpose, tool.description] + tool.tags
        search_blob = " ".join(filter(None, metadata)).lower()
        candidates.append((tool, search_blob))
    corpus = {tool.name: blob for tool, blob in candidates}
    match_blobs = list(corpus.values())
    matches = get_close_matches(
        task_description.lower(), match_blobs, n=top_k, cutoff=threshold
    )
    ranked = [tool for tool, blob in candidates if blob in matches]
    if return_all_matches:
        logger.debug("Returning all ranked matches: %s", [t.name for t in ranked])
        return ranked
    logger.debug("Returning best match: %s", ranked[0].name if ranked else None)
    return ranked[0] if ranked else None
