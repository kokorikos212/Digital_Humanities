"""
Shared utilities for tool metadata generation and serialization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel


def generate_tool_metadata(name: str, model: Type[BaseModel]) -> Dict[str, Any]:
    """Convert a Pydantic input model into the OpenAI/DeepSeek tool definition dict."""
    schema = model.model_json_schema()
    schema.pop("title", None)
    if "properties" in schema:
        for prop in schema["properties"].values():
            prop.pop("title", None)
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": model.__doc__ or "",
            "parameters": schema,
        },
    }


def build_tool_definitions(*registries: List[Tuple[str, Type[BaseModel]]]) -> List[Dict[str, Any]]:
    """Flatten multiple (name, model) registries into a single tool-definition list."""
    definitions: List[Dict[str, Any]] = []
    for registry in registries:
        for name, model in registry:
            definitions.append(generate_tool_metadata(name, model))
    return definitions
