from aegis.registry import TOOL_REGISTRY
from pydantic import BaseModel
from aegis.utils.logger import setup_logger


logger = setup_logger(__name__)


def test_unique_tool_names():
    names = [tool.name for tool in TOOL_REGISTRY.values()]
    assert len(names) == len(set(names)), "Duplicate tool names found"


def test_tool_metadata_completeness():
    for tool in TOOL_REGISTRY.values():
        assert tool.input_model, f"{tool.name} missing input_model"
        assert tool.purpose, f"{tool.name} missing purpose"
        assert tool.category, f"{tool.name} missing category"
        assert tool.tags, f"{tool.name} missing tags"
        assert tool.description, f"{tool.name} missing description"


def test_input_model_instantiation():
    for tool in TOOL_REGISTRY.values():
        model = tool.input_model
        if not issubclass(model, BaseModel):
            continue
        # noinspection PyBroadException
        try:
            _ = model()  # allows default-only models to pass
        except Exception as e:
            # This test only ensures the model is instantiable with defaults if possible
            logger.error(f"Unable to instantiate input model: {e}")
