# aegis/tools/wrappers/structured_parsing.py
"""
A wrapper tool for using an LLM to reliably extract structured data from text.
"""
from typing import Dict, Any

from pydantic import BaseModel, Field, create_model

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.registry import register_tool
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import instructor
    from openai import OpenAI
except ImportError:
    instructor = None
    OpenAI = None


class ExtractStructuredDataInput(BaseModel):
    """Input for extracting structured data from a block of text.

    :ivar text_to_parse: The unstructured text to extract information from.
    :vartype text_to_parse: str
    :ivar extraction_schema: A JSON schema defining the desired output structure.
    :vartype extraction_schema: Dict[str, Any]
    """

    text_to_parse: str = Field(
        ..., description="The unstructured text to extract information from."
    )
    extraction_schema: Dict[str, Any] = Field(
        ...,
        description="A JSON schema defining the desired output structure. "
        'Example: {"properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}',
    )


@register_tool(
    name="extract_structured_data",
    input_model=ExtractStructuredDataInput,
    description="Uses an LLM to parse unstructured text and extract data that conforms to a specified JSON schema. Returns the validated, structured data.",
    category="parsing",
    tags=["parsing", "structured-data", "instructor", "wrapper"],
    safe_mode=True,
    purpose="Extract structured information from unstructured text.",
)
def extract_structured_data(
    input_data: ExtractStructuredDataInput, state: TaskState
) -> Dict[str, Any]:
    """
    Dynamically creates a Pydantic model from a schema, then uses Instructor
    to force an LLM to extract data from text into that model.

    :param input_data: The text to parse and the schema to conform to.
    :type input_data: ExtractStructuredDataInput
    :param state: The current agent task state, used to get backend config.
    :type state: TaskState
    :return: A dictionary containing the extracted and validated data.
    :rtype: Dict[str, Any]
    """
    if not instructor or not OpenAI:
        raise ToolExecutionError(
            "The 'instructor' and 'openai' libraries are required for this tool."
        )

    logger.info(
        f"Executing tool: extract_structured_data with schema: {input_data.extraction_schema.get('properties', {}).keys()}"
    )

    try:
        # Dynamically create a Pydantic model from the provided schema
        DynamicExtractionModel = create_model(
            "DynamicExtractionModel",
            **{
                name: (details.get("type", "string"), Field(...))
                for name, details in input_data.extraction_schema["properties"].items()
            },
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Failed to create dynamic Pydantic model from schema: {e}"
        )

    # Get the URL of the currently configured LLM backend
    if not state.runtime.backend_profile:
        raise ConfigurationError(
            "Backend profile is not set in the current task state."
        )

    try:
        backend_config = get_backend_config(state.runtime.backend_profile)
        # This assumes the backend has an OpenAI-compatible endpoint URL
        backend_url = getattr(backend_config, "llm_url", None)
        if not backend_url:
            raise ConfigurationError(
                f"Backend profile '{state.runtime.backend_profile}' does not have a configurable 'llm_url'."
            )
        # vLLM uses /v1/chat/completions, but instructor needs the base /v1/
        base_url = backend_url.rsplit("/", 1)[0]

    except Exception as e:
        raise ConfigurationError(f"Could not load backend configuration: {e}")

    try:
        # Instantiate and patch an OpenAI client to point to our local backend
        client = instructor.patch(
            OpenAI(base_url=base_url, api_key="not-needed-for-local")
        )

        # Call the LLM with the response_model parameter to get structured output
        extracted_data = client.chat.completions.create(
            model=getattr(backend_config, "model", "default-model"),
            messages=[
                {
                    "role": "user",
                    "content": f"Extract the relevant information from the following text, conforming to the provided schema:\n\nText:\n'''{input_data.text_to_parse}'''",
                }
            ],
            response_model=DynamicExtractionModel,
        )

        # Return the validated data as a dictionary
        return extracted_data.model_dump()
    except Exception as e:
        logger.exception("Instructor-based data extraction failed.")
        raise ToolExecutionError(f"LLM data extraction failed: {e}")
