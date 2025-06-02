"""
Inventory route to expose currently registered tools and their metadata.
"""

from fastapi import APIRouter

from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/inventory")
async def get_inventory():
    """
    get_inventory.
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_inventory] Entering def()")
    return [
        {
            "name": tool.name,
            "category": tool.category or "unspecified",
            "tags": tool.tags,
            "description": tool.description,
        }
        for tool in TOOL_REGISTRY.values()
    ]
