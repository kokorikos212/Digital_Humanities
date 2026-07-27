"""
Tests for the pipeline tool-filtering functionality.

Verifies that ``filter_tool_definitions`` and ``get_enabled_handler_categories``
correctly gate which tools are sent to the LLM.  No API calls required.
"""

from __future__ import annotations

import pytest

from src.tools import (
    ALL_TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    TOOL_UI_LABELS,
    filter_tool_definitions,
    get_enabled_handler_categories,
)


class TestToolFiltering:
    """Verify the tool-filtering machinery used by pipeline + UI."""

    def test_filter_all_tools_when_empty_set(self):
        """Passing an empty set should return all tool definitions."""
        result = filter_tool_definitions(set())
        assert len(result) == len(ALL_TOOL_DEFINITIONS)

    def test_filter_single_tool(self):
        """Passing {'get_tags'} should return only that definition."""
        result = filter_tool_definitions({"get_tags"})
        assert len(result) == 1
        assert result[0]["function"]["name"] == "get_tags"

    def test_filter_multiple_tools(self):
        """Passing two tool names should return exactly those two definitions."""
        result = filter_tool_definitions({"get_tags", "generate_triples"})
        names = {td["function"]["name"] for td in result}
        assert names == {"get_tags", "generate_triples"}

    def test_filter_unknown_tool_returns_empty(self):
        """Passing a tool name that doesn't exist should return empty list."""
        result = filter_tool_definitions({"nonexistent_tool"})
        assert len(result) == 0

    def test_all_ui_labels_have_corresponding_tool(self):
        """Every UI label should correspond to a tool in ALL_TOOL_DEFINITIONS."""
        all_names = {td["function"]["name"] for td in ALL_TOOL_DEFINITIONS}
        for tool_name in TOOL_UI_LABELS:
            assert tool_name in all_names, (
                f"UI label '{tool_name}' has no matching tool definition"
            )

    def test_get_enabled_handler_categories_empty(self):
        """Empty set should return all handler categories."""
        result = get_enabled_handler_categories(set())
        assert result == set(TOOL_HANDLERS.keys())

    def test_get_enabled_handler_categories_single(self):
        """A single tool should map to its handler category."""
        result = get_enabled_handler_categories({"get_tags"})
        assert "linguistic" in result

    def test_get_enabled_handler_categories_multiple(self):
        """Tools from different categories should return all those categories."""
        result = get_enabled_handler_categories(
            {"get_tags", "generate_triples"}
        )
        assert "linguistic" in result
        assert "triple_generator" in result
        # These should NOT be included
        assert "graph_builder" not in result
        assert "obsidian_builder" not in result


class TestToolDefinitionsValidity:
    """Structural checks on tool definitions."""

    def test_all_definitions_have_required_fields(self):
        """Every tool definition must follow OpenAI function-calling schema."""
        for td in ALL_TOOL_DEFINITIONS:
            assert td["type"] == "function"
            func = td["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            params = func["parameters"]
            assert params["type"] == "object"

    def test_no_duplicate_tool_names(self):
        """Tool function names must be unique."""
        names = [td["function"]["name"] for td in ALL_TOOL_DEFINITIONS]
        assert len(names) == len(set(names)), (
            f"Duplicate tool names found: {names}"
        )

    def test_essential_tools_exist(self):
        """The core pipeline tools should all be registered."""
        names = {td["function"]["name"] for td in ALL_TOOL_DEFINITIONS}
        essential = {
            "get_tags", "generate_viz", "generate_triples",
            "analyze_conversation", "build_obsidian_note",
            "generate_semantic_graph", "write_file",
        }
        missing = essential - names
        assert not missing, f"Missing essential tools: {missing}"
