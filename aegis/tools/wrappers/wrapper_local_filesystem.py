# aegis/tools/wrappers/wrapper_local_filesystem.py
"""
A suite of safe, high-level tools for interacting with the local filesystem.

These tools provide intuitive, goal-oriented actions for common file
operations, using Python's robust `pathlib` library for safety and
reliability. They are intended to be the primary way for an agent to
manage local files and directories.
"""
from pathlib import Path

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class DirectoryPathInput(BaseModel):
    path: str = Field(..., description="The path to the directory.")


class FilePathInput(BaseModel):
    path: str = Field(..., description="The path to the file.")


class WriteFileInput(BaseModel):
    path: str = Field(..., description="The path to the file.")
    content: str = Field(..., description="The content to write into the file.")


# --- Tools ---


@register_tool(
    name="create_directory",
    input_model=DirectoryPathInput,
    description="Creates a new directory at the specified path. This tool is safe and preferred for creating folders.",
    category="filesystem",
    tags=["local", "file", "directory", "create", "safe"],
    safe_mode=True,
)
def create_directory(input_data: DirectoryPathInput) -> str:
    """Safely creates a directory, including any necessary parent directories."""
    logger.info(f"Executing tool: create_directory with path '{input_data.path}'")
    try:
        path = Path(input_data.path)
        path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory at: {input_data.path}"
    except Exception as e:
        error_msg = f"Failed to create directory at '{input_data.path}': {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)


@register_tool(
    name="write_to_file",
    input_model=WriteFileInput,
    description="Writes (or overwrites) content to a file at the specified path. Creates the file if it does not exist. This tool is safe and preferred for writing files.",
    category="filesystem",
    tags=["local", "file", "write", "create", "safe"],
    safe_mode=True,
)
def write_to_file(input_data: WriteFileInput) -> str:
    """Safely writes content to a local file."""
    logger.info(f"Executing tool: write_to_file with path '{input_data.path}'")
    try:
        path = Path(input_data.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input_data.content, encoding="utf-8")
        return f"Successfully wrote {len(input_data.content)} characters to file: {input_data.path}"
    except Exception as e:
        error_msg = f"Failed to write to file at '{input_data.path}': {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)


@register_tool(
    name="read_file",
    input_model=FilePathInput,
    description="Reads and returns the content of a file from the specified path. This tool is safe and preferred for reading files.",
    category="filesystem",
    tags=["local", "file", "read", "safe"],
    safe_mode=True,
)
def read_file(input_data: FilePathInput) -> str:
    """Safely reads content from a local file."""
    logger.info(f"Executing tool: read_file with path '{input_data.path}'")
    try:
        path = Path(input_data.path)
        if not path.is_file():
            raise FileNotFoundError("File does not exist at the specified path.")
        content = path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        error_msg = f"Failed to read file at '{input_data.path}': {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)


@register_tool(
    name="delete_file",
    input_model=FilePathInput,
    description="Deletes a file at the specified path. This tool is safe and preferred for deleting files.",
    category="filesystem",
    tags=["local", "file", "delete", "remove", "safe"],
    safe_mode=True,
)
def delete_file(input_data: FilePathInput) -> str:
    """Safely deletes a local file."""
    logger.info(f"Executing tool: delete_file with path '{input_data.path}'")
    try:
        path = Path(input_data.path)
        if not path.is_file():
            raise FileNotFoundError("File does not exist at the specified path.")
        path.unlink()
        return f"Successfully deleted file: {input_data.path}"
    except Exception as e:
        error_msg = f"Failed to delete file at '{input_data.path}': {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)
