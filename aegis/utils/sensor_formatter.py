"""Formats and validates outputs from sensor-style tools such as Nmap or packet capture.
Ensures compatibility with downstream structured consumption."""

from typing import Dict, List, Any

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def format_sensor_context(sensor_outputs: Dict[str, List[Any]]) -> str:
    """
    Convert structured sensor output data into a readable text block.

    :param sensor_outputs: Dictionary of tool name → list of structured results
    :return: Multiline string with annotated context
    """
    if not sensor_outputs:
        logger.info("No sensor data provided")
        return "No sensor data available."

    output_lines = []
    logger.info(f"Formatting output from {len(sensor_outputs)} tool(s)")

    for tool, entries in sensor_outputs.items():
        output_lines.append(f"🔧 Tool: {tool}")
        logger.debug(f"{tool}: {len(entries)} entries")
        for i, entry in enumerate(entries, start=1):
            if isinstance(entry, dict):
                for k, v in entry.items():
                    output_lines.append(f"  [{i}] {k}: {v}")
            else:
                output_lines.append(f"  [{i}] {entry}")
    return "\n".join(output_lines)
