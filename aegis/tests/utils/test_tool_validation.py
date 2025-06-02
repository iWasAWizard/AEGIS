from aegis.registry import TOOL_REGISTRY

VALID_CATEGORIES = {
    "system",
    "network",
    "diagnostic",
    "file_ops",
    "llm",
    "monitoring",
    "auth",
    "integration",
}


def is_valid_tag(tag: str) -> bool:
    return (
        tag.islower()
        and tag.replace("_", "").isalnum()
        and " " not in tag
        and "-" not in tag
    )


def test_tool_registry_metadata():
    errors = []

    for name, tool in TOOL_REGISTRY.items():
        if not tool.description:
            errors.append(f"[{name}] Missing description.")
        if not tool.input_model:
            errors.append(f"[{name}] Missing input model.")
        if tool.safe_mode not in (True, False):
            errors.append(f"[{name}] Missing or invalid safe_mode flag.")

        if tool.category not in VALID_CATEGORIES:
            errors.append(f"[{name}] Invalid category: '{tool.category}'")

        for tag in tool.tags:
            if not is_valid_tag(tag):
                errors.append(f"[{name}] Invalid tag: '{tag}'")

    assert not errors, "\n".join(errors)
