"""
Agent tool registry — assembles all tool definitions and handler mappings.

Provides ``filter_tool_definitions()`` to selectively enable/disable tools
at runtime (used by the Gradio UI tool-toggling feature).
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple, Type

from pydantic import BaseModel

from .linguistics import LinguisticTools, linguistic_registry
from .writer import FolderRestrictedAgent, write_registry
from .triples import TripleGenerator, triple_generator_registry
from .conversation import ConversationAnalyzer, conversation_analyzer_registry
from .obsidian import ObsidianBuilder, obsidian_builder_registry
from .graph import GraphBuilder, graph_builder_registry
from .utils import build_tool_definitions

# ── 1. Collect all registries ────────────────────────────────────────────

ALL_REGISTRIES: List[Tuple[str, Type[BaseModel]]] = (
    linguistic_registry
    + write_registry
    + triple_generator_registry
    + conversation_analyzer_registry
    + obsidian_builder_registry
    + graph_builder_registry
)

# ── 2. Build the full tool-definition list for the LLM ───────────────────

ALL_TOOL_DEFINITIONS: List[Dict[str, Any]] = build_tool_definitions(
    linguistic_registry,
    write_registry,
    triple_generator_registry,
    conversation_analyzer_registry,
    obsidian_builder_registry,
    graph_builder_registry,
)

# ── 3. Handler map — keys are tool function names ─────────────────────────

TOOL_HANDLERS: Dict[str, Any] = {
    "linguistic": LinguisticTools,
    "writer": FolderRestrictedAgent,
    "triple_generator": TripleGenerator,
    "conversation_analyzer": ConversationAnalyzer,
    "obsidian_builder": ObsidianBuilder,
    "graph_builder": GraphBuilder,
}

# ── 4. Tool name → handler category mapping ──────────────────────────────

TOOL_CATEGORY_MAP: Dict[str, str] = {
    "get_tags": "linguistic",
    "generate_viz": "linguistic",
    "visualize_syntax": "linguistic",  # safety alias
    "write_file": "writer",
    "generate_triples": "triple_generator",
    "analyze_conversation": "conversation_analyzer",
    "build_obsidian_note": "obsidian_builder",
    "generate_semantic_graph": "graph_builder",
}

# ── 5. UI-friendly tool labels for the checkbox group ─────────────────────

TOOL_UI_LABELS: Dict[str, str] = {
    "get_tags": "Linguistic Parsing (spaCy POS/NER/Dependencies)",
    "generate_viz": "Dependency Tree Visualization (displaCy SVG)",
    "generate_triples": "RDF Triple Generation (Turtle / Knowledge Graph)",
    "analyze_conversation": "Conversation Analysis (Speakers / Pragmatics)",
    "build_obsidian_note": "Obsidian Vault Note Builder (Markdown + Wikilinks)",
    "generate_semantic_graph": "Semantic Network Visualizer (Pyvis Interactive HTML)",
    "write_file": "Write Markdown Report",
}

# ── 6. Public API ────────────────────────────────────────────────────────


def filter_tool_definitions(
    enabled_tools: Set[str],
) -> List[Dict[str, Any]]:
    """Return only the tool definitions for the *enabled_tools* names.

    Parameters
    ----------
    enabled_tools:
        Set of tool function names to enable (e.g. ``{"get_tags", "generate_triples"}``).

    Returns
    -------
    A filtered list of tool-definition dicts ready to pass to the LLM.
    """
    if not enabled_tools:
        return ALL_TOOL_DEFINITIONS  # empty → enable all

    return [
        td
        for td in ALL_TOOL_DEFINITIONS
        if td["function"]["name"] in enabled_tools
    ]


def get_enabled_handler_categories(enabled_tools: Set[str]) -> Set[str]:
    """Return the handler category keys needed for the *enabled_tools* set."""
    if not enabled_tools:
        return set(TOOL_HANDLERS.keys())

    categories: Set[str] = set()
    for name in enabled_tools:
        cat = TOOL_CATEGORY_MAP.get(name)
        if cat:
            categories.add(cat)
    return categories


__all__ = [
    "ALL_TOOL_DEFINITIONS",
    "ALL_REGISTRIES",
    "TOOL_HANDLERS",
    "TOOL_CATEGORY_MAP",
    "TOOL_UI_LABELS",
    "filter_tool_definitions",
    "get_enabled_handler_categories",
]
