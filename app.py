#!/usr/bin/env python3
"""
Gradio Web UI for the Ontological Conversation Analysis Pipeline.

Features:
  - Dynamic tool selection (checkbox group) — only selected tools execute
  - Text input + pre-loaded example selector
  - Tabbed output: JSON summary, Turtle RDF, semantic graph, Obsidian notes
  - Designed for iframe embedding in GitHub Pages

Usage:
    python app.py                 # launch locally
    python app.py --share         # create a public Gradio link
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set

import gradio as gr

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import html as _html

from src.config import config
from src.pipeline import run_pipeline
from src.prompts import SYSTEM_PROMPT, NAMED_PROMPTS, build_analysis_prompt
from src.tools import TOOL_UI_LABELS
from src.visualizer import render_rdf_graph

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

EXAMPLES = {
    "Single Sentence (Dr. Chen)": (
        "Dr. Chen presented the research findings at Stanford University "
        "last Tuesday. The professor argued that machine learning models "
        "can detect bias in political speeches."
    ),
    "Conversation (Student & Professor)": (
        "**Alice:** Good morning, Professor. Could you review my thesis draft?\n\n"
        "**Professor:** Of course, Alice. I'll have comments by Friday.\n\n"
        "**Alice:** Thank you so much! I was worried about the methodology section.\n\n"
        "**Professor:** The statistical approach looks sound. Just expand the "
        "literature review."
    ),
    "Political Debate Excerpt": (
        "**Moderator:** Senator, what is your position on the climate bill?\n\n"
        "**Senator Harris:** The legislation is crucial. It creates green jobs "
        "while reducing emissions by 40% over the next decade.\n\n"
        "**Moderator:** Congressman Lee, your response?\n\n"
        "**Congressman Lee:** With respect, those numbers are fantasy. The "
        "Congressional Budget Office analysis shows it would cost taxpayers "
        "over $2 trillion with negligible environmental benefit."
    ),
    "The quick brown fox": (
        "The quick brown fox jumps over the lazy dog."
    ),
}

DEFAULT_EXAMPLE = "Single Sentence (Dr. Chen)"

# ═══════════════════════════════════════════════════════════════════════════
# Pipeline runner
# ═══════════════════════════════════════════════════════════════════════════


def run_analysis(
    text: str,
    enable_linguistics: bool,
    enable_triples: bool,
    enable_graph: bool,
    enable_obsidian: bool,
    enable_conversation: bool,
    enable_viz: bool,
) -> tuple[str, str, str, str]:
    """Execute the pipeline with the user's text and tool selections.

    Returns
    -------
    (json_output, rdf_output, graph_html, obsidian_md)
        Four strings for the four output tabs.
    """
    if not text or not text.strip():
        return (
            "⚠️ Please enter some text to analyze.",
            "",
            "<p style='color:#888'>No graph generated.</p>",
            "",
        )

    # Build the enabled-tools set from checkbox values
    enabled: Set[str] = set()
    if enable_linguistics:
        enabled.add("get_tags")
    if enable_triples:
        enabled.add("generate_triples")
    if enable_graph:
        enabled.add("generate_semantic_graph")
    if enable_obsidian:
        enabled.add("build_obsidian_note")
    if enable_conversation:
        enabled.add("analyze_conversation")
    if enable_viz:
        enabled.add("generate_viz")

    # Load config
    try:
        config.load_env()
    except RuntimeError:
        pass  # will fail inside run_pipeline if key missing

    # Build the prompt
    tool_descriptions = {
        "get_tags": "POS tagging, NER, and dependency parsing",
        "generate_triples": "RDF triple generation",
        "generate_semantic_graph": "interactive network visualization",
        "build_obsidian_note": "Obsidian markdown notes",
        "analyze_conversation": "conversation structure analysis",
        "generate_viz": "dependency tree SVG visualization",
    }

    enabled_desc = ", ".join(
        f"{name} ({tool_descriptions[name]})"
        for name in sorted(enabled)
    ) or "no tools selected"

    user_prompt = (
        f"Perform an ontological analysis on the following text using "
        f"only these tools: {enabled_desc}.\n\n"
        f"For each tool you call, provide the results in a structured JSON "
        f"response. If conversation analysis is requested and the text "
        f"contains speaker turns, also analyze the conversation structure.\n\n"
        f"Text to analyze:\n---\n{text.strip()}\n---\n\n"
        f"When finished, return a concise JSON summary."
    )

    # Run pipeline
    try:
        start = time.monotonic()
        result = run_pipeline(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_iterations=30,
            enabled_tools=enabled,
        )
        elapsed = time.monotonic() - start
    except Exception as exc:
        tb = traceback.format_exc()
        return (
            f"❌ Pipeline error:\n\n```\n{tb}\n```",
            "",
            "<p style='color:#c00'>Graph generation failed.</p>",
            "",
        )

    # ── Gather output artifacts ───────────────────────────────────────

    # 1. JSON summary — the LLM's final response
    json_output = result
    if elapsed:
        json_output = (
            f"_Completed in {elapsed:.1f}s with tools: "
            f"{', '.join(sorted(enabled)) or 'none'}_\n\n{result}"
        )

    # 2. Turtle RDF — find the most recent .ttl file
    rdf_output = ""
    rdf_dir = config.rdf_dir
    if rdf_dir.exists():
        ttl_files = sorted(rdf_dir.glob("ontology_*.ttl"), reverse=True)
        if ttl_files:
            rdf_output = ttl_files[0].read_text(encoding="utf-8")

    # 3. Semantic graph HTML — render RDF via Talos visualizer
    graph_html = _format_graph_html(rdf_output)

    # 4. Obsidian notes — most recent .md
    obsidian_md = ""
    verse_dir = config.verse_dir
    if verse_dir.exists():
        md_files = sorted(verse_dir.glob("*.md"), reverse=True)
        if md_files and md_files[0].name != "Untitled.md":
            obsidian_md = md_files[0].read_text(encoding="utf-8")

    return json_output, rdf_output, graph_html, obsidian_md


def _format_graph_html(ttl_data: str) -> str:
    """Render TTL string to PyVis HTML and wrap in an iframe for Gradio."""
    if not ttl_data or not ttl_data.strip():
        return (
            "<div style='padding:20px;text-align:center;color:#666;'>"
            "No graph data available.</div>"
        )
    try:
        raw_html = render_rdf_graph(ttl_data, height="650px")
        return (
            f'<iframe srcdoc="{_html.escape(raw_html)}" '
            f'width="100%" height="670px" '
            f'style="border:none;border-radius:8px;"></iframe>'
        )
    except Exception as exc:
        return (
            f"<div style='color:red;padding:20px;'>"
            f"Error rendering graph: {_html.escape(str(exc))}</div>"
        )


def load_example(name: str) -> str:
    """Load a pre-defined example by name."""
    return EXAMPLES.get(name, "")


# ═══════════════════════════════════════════════════════════════════════════
# Gradio UI
# ═══════════════════════════════════════════════════════════════════════════


UI_CSS = """
.app-container { max-width: 960px; margin: 0 auto; }
.output-box textarea { font-family: 'JetBrains Mono', 'Fira Code', monospace !important; font-size: 13px !important; }
footer { display: none !important; }
#title { text-align: center; margin-bottom: 0; }
#subtitle { text-align: center; color: #888; margin-top: 0; }
"""


def create_ui() -> gr.Blocks:
    """Build the Gradio interface."""

    with gr.Blocks(
        theme=gr.themes.Soft(),
        head="""<meta name="viewport" content="width=device-width, initial-scale=1.0">""",
        title="Ontological Discourse Analysis",
        css=UI_CSS,
    ) as app:

        # ── Header ──────────────────────────────────────────────────
        gr.Markdown(
            """
            # 🔬 Ontological Discourse Analysis
            Map conversational text to structured ontologies — RDF triples,
            semantic networks, and Obsidian knowledge graphs.
            """,
            elem_id="title",
        )

        # ── Input Section ───────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                text_input = gr.Textbox(
                    label="Text to Analyze",
                    placeholder="Paste text or a conversation here...\n\nExample:\nAlice: Hello Professor!\nBob: Good morning, Alice.",
                    lines=8,
                    value=EXAMPLES[DEFAULT_EXAMPLE],
                )
            with gr.Column(scale=2):
                example_selector = gr.Dropdown(
                    label="📋 Load Example",
                    choices=list(EXAMPLES.keys()),
                    value=DEFAULT_EXAMPLE,
                )

        # ── Tool Selector ───────────────────────────────────────────
        gr.Markdown("### 🛠️ Select Tools to Activate")
        with gr.Row():
            with gr.Column(scale=1):
                enable_linguistics = gr.Checkbox(
                    value=True,
                    label=TOOL_UI_LABELS["get_tags"],
                    info="POS tags, NER, dependencies, noun chunks",
                )
                enable_triples = gr.Checkbox(
                    value=True,
                    label=TOOL_UI_LABELS["generate_triples"],
                    info="RDF triples (Turtle / JSON-LD)",
                )
                enable_conversation = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["analyze_conversation"],
                    info="Speakers, reply graphs, pragmatics",
                )
            with gr.Column(scale=1):
                enable_graph = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["generate_semantic_graph"],
                    info="Interactive pyvis HTML graph",
                )
                enable_obsidian = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["build_obsidian_note"],
                    info="Markdown notes with [[wikilinks]]",
                )
                enable_viz = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["generate_viz"],
                    info="displaCy SVG dependency tree",
                )

        # ── Run Button ──────────────────────────────────────────────
        with gr.Row():
            run_btn = gr.Button("🔍 Analyze", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear", size="lg")

        # ── Status ──────────────────────────────────────────────────
        status = gr.Markdown("")

        # ── Output Tabs ─────────────────────────────────────────────
        with gr.Tabs():
            with gr.TabItem("📊 JSON Summary"):
                json_output = gr.Code(
                    label="Analysis Result",
                    language="json",
                    lines=20,
                    elem_classes="output-box",
                )

            with gr.TabItem("🐢 RDF Triples (Turtle)"):
                rdf_output = gr.Code(
                    label="RDF Serialization",
                    lines=20,
                    elem_classes="output-box",
                )

            with gr.TabItem("🕸️ Semantic Graph"):
                graph_output = gr.HTML(
                    label="Interactive Network",
                    value="<p style='color:#888;padding:2em;text-align:center'>"
                    "Enable <b>Semantic Network Visualizer</b> and run analysis "
                    "to see the graph here.</p>",
                )

            with gr.TabItem("📝 Obsidian Note"):
                obsidian_output = gr.Code(
                    label="Generated Markdown",
                    language="markdown",
                    lines=20,
                    elem_classes="output-box",
                )

        # ── Event Handlers ──────────────────────────────────────────

        example_selector.change(
            fn=load_example,
            inputs=[example_selector],
            outputs=[text_input],
        )

        run_btn.click(
            fn=lambda: "⏳ Running analysis...",
            outputs=[status],
        ).then(
            fn=run_analysis,
            inputs=[
                text_input,
                enable_linguistics,
                enable_triples,
                enable_graph,
                enable_obsidian,
                enable_conversation,
                enable_viz,
            ],
            outputs=[json_output, rdf_output, graph_output, obsidian_output],
        ).then(
            fn=lambda: "✅ Analysis complete.",
            outputs=[status],
        )

        clear_btn.click(
            fn=lambda: ("", "", "", "", ""),
            outputs=[
                text_input,
                json_output,
                rdf_output,
                obsidian_output,
                status,
            ],
        )

    return app


# ═══════════════════════════════════════════════════════════════════════════
# HF Spaces requires the Blocks object at module level as `demo`
# ═══════════════════════════════════════════════════════════════════════════

demo = create_ui()
demo.queue()

# ═══════════════════════════════════════════════════════════════════════════
# Entry point (local dev)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gradio UI for Ontological Discourse Analysis"
    )
    parser.add_argument(
        "--share", action="store_true",
        help="Create a public Gradio share link",
    )
    parser.add_argument(
        "--port", type=int, default=7860,
        help="Port to listen on (default: 7860)",
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True,
    )
