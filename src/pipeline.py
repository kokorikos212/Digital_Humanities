"""
Agentic pipeline for ontological conversation analysis.

Connects an LLM (DeepSeek) to a suite of linguistic and knowledge-graph
tools.  The agent orchestrates: linguistic annotation → conversation
analysis → triple generation → Obsidian note building → graph visualization.

Supports dynamic tool filtering via ``enabled_tools`` so the Gradio UI
can let users select which tools to activate per run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List, Optional, Set

import openai

from src.config import config
from src.tools import (
    ALL_TOOL_DEFINITIONS,
    TOOL_CATEGORY_MAP,
    TOOL_HANDLERS,
    filter_tool_definitions,
    get_enabled_handler_categories,
)


def _build_tool_map(enabled_tools: Set[str]) -> Dict:
    """Instantiate handlers and build the function-name → callable mapping.

    Only creates handlers for categories actually used by *enabled_tools*.
    """
    categories = get_enabled_handler_categories(enabled_tools)

    handlers: Dict[str, Any] = {}
    if "linguistic" in categories:
        handlers["linguistic"] = TOOL_HANDLERS["linguistic"]()
    if "writer" in categories:
        handlers["writer"] = TOOL_HANDLERS["writer"]()
    if "triple_generator" in categories:
        handlers["triple_generator"] = TOOL_HANDLERS["triple_generator"]()
    if "conversation_analyzer" in categories:
        handlers["conversation_analyzer"] = TOOL_HANDLERS["conversation_analyzer"]()
    if "obsidian_builder" in categories:
        handlers["obsidian_builder"] = TOOL_HANDLERS["obsidian_builder"]()
    if "graph_builder" in categories:
        handlers["graph_builder"] = TOOL_HANDLERS["graph_builder"]()

    return {
        "get_tags": handlers["linguistic"].get_tags if "linguistic" in handlers else None,
        "generate_viz": handlers["linguistic"].generate_viz if "linguistic" in handlers else None,
        "visualize_syntax": handlers["linguistic"].generate_viz if "linguistic" in handlers else None,
        "write_file": handlers["writer"].write_file if "writer" in handlers else None,
        "generate_triples": handlers["triple_generator"].generate_triples if "triple_generator" in handlers else None,
        "analyze_conversation": handlers["conversation_analyzer"].analyze_conversation if "conversation_analyzer" in handlers else None,
        "build_obsidian_note": handlers["obsidian_builder"].build_obsidian_note if "obsidian_builder" in handlers else None,
        "generate_semantic_graph": handlers["graph_builder"].generate_semantic_graph if "graph_builder" in handlers else None,
    }


def run_pipeline(
    user_prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    max_iterations: int = 30,
    model: str = "deepseek-chat",
    enabled_tools: Optional[Set[str]] = None,
) -> str:
    """Execute the agentic tool-calling loop.

    Parameters
    ----------
    user_prompt:
        The task for the agent (e.g. analyze a conversation).
    system_prompt:
        System-level instruction for the LLM persona.
    max_iterations:
        Safety limit for the tool-calling loop.
    model:
        LLM model name.
    enabled_tools:
        Set of tool function names to enable.  Pass an empty set or None
        to enable all tools.  Example: ``{"get_tags", "generate_triples"}``.

    Returns
    -------
    The final text response from the LLM, or an error message.
    """
    # ── Resolve enabled tools ─────────────────────────────────────────
    tools_enabled = enabled_tools or set()
    tool_defs = filter_tool_definitions(tools_enabled)
    tool_map = _build_tool_map(tools_enabled)

    # ── Create API client ─────────────────────────────────────────────
    client = openai.OpenAI(
        api_key=config.deepseek_key, base_url=config.deepseek_base_url
    )

    # ── Messages ──────────────────────────────────────────────────────
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for iteration in range(1, max_iterations + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_defs,
            tool_choice="auto",
            response_format={"type": "json_object"},
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            return response_message.content or ""

        messages.append(response_message)

        for tool_call in tool_calls:
            func_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                result = f"Error: could not parse arguments for {func_name}"
            else:
                print(f"DEBUG [Iter {iteration}]: LLM called {func_name}")

                handler = tool_map.get(func_name)
                if handler is not None:
                    try:
                        result = handler(**args)
                    except Exception as exc:
                        result = f"Error executing {func_name}: {exc}"
                else:
                    result = f"Error: Tool '{func_name}' is not registered."

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    return "Max iterations reached without a final answer."


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.prompts import NAMED_PROMPTS, SYSTEM_PROMPT

    config.load_env()

    user_prompt = NAMED_PROMPTS.get(
        "ex_combined", NAMED_PROMPTS.get("ex_file", "Analyze a sentence.")
    )

    result = run_pipeline(user_prompt, system_prompt=SYSTEM_PROMPT)
    print(result)
