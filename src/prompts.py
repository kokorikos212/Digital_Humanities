"""
Prompt templates for the ontological analysis pipeline.

Previously stored as JSON files in ``agent/database/``.
Now they are Python constants — source code, not runtime data.
"""

from __future__ import annotations

import textwrap
from typing import Dict

# ═══════════════════════════════════════════════════════════════════════════════
# System prompt (LLM persona)
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are a precise linguistic ontologist. Your purpose is to map "
    "conversational text to structured ontologies. You have access to "
    "these tools: (1) get_tags — POS tagging, NER, dependency parsing; "
    "(2) generate_viz — displaCy SVG trees; "
    "(3) analyze_conversation — conversation structure and pragmatics via Convokit; "
    "(4) generate_triples — convert entities+relations into RDF triples; "
    "(5) build_obsidian_note — save ontological findings as Obsidian .md "
    "with YAML frontmatter and [[wikilinks]]; "
    "(6) generate_semantic_graph — interactive pyvis HTML graph of entities "
    "and relations; (7) write_file — save arbitrary markdown reports. "
    "Follow this execution logic strictly: "
    "1. Call get_tags on the text to obtain tokens, entities, dependencies, "
    "and noun chunks. "
    "2. If the text is conversational (has speaker turns), call "
    "analyze_conversation to extract speaker structure and pragmatics. "
    "3. Call generate_triples with the entities and relations extracted "
    "from steps 1-2. "
    "4. Call build_obsidian_note to persist the ontological structures as "
    "an Obsidian note with [[wikilinks]] linking entities. "
    "5. Call generate_semantic_graph to produce an interactive network "
    "visualization of the ontology. "
    "6. Optionally call write_file for a final narrative summary. "
    "Do not narrate your process or comment on tool outputs. When you have "
    "completed the tool chain, provide a concise JSON summary following the "
    "OntologicalAnalysis schema with analysis_id, source_text, ontology "
    "(entities and triples), obsidian_notes, visualizations, and summary fields."
)

# ═══════════════════════════════════════════════════════════════════════════════
# Named prompt templates
# ═══════════════════════════════════════════════════════════════════════════════

NAMED_PROMPTS: Dict[str, str] = {
    "ex_prompt": "You are a helpful assistant that can analyze text and write markdown reports.",
    "ex_analysis": (
        "Analyze the following text and create a report on the phrase: "
        "'The quick brown fox jumps over the lazy dog.'"
    ),
    "ex_visualization": (
        "Analyze the following text and create a report on the phrase: "
        "'The quick brown fox jumps over the lazy dog', create a visualization "
        "of the analysis."
    ),
    "ex_file": (
        "Analyze the following text and create a report on the phrase: "
        "'The quick brown fox jumps over the lazy dog', write the report to "
        "a markdown file named 'report.md'."
    ),
    "ex_combined": (
        "Analyze the following text and create a report on the phrase: "
        "'The quick brown fox jumps over the lazy dog', create a visualization "
        "of the analysis, and write the report to a markdown file named "
        "'report.md'."
    ),
    "ex_ontology_basic": (
        "Perform a full ontological analysis on this text: "
        "'Dr. Chen presented the research findings at Stanford University "
        "last Tuesday. The professor argued that machine learning models can "
        "detect bias in political speeches.' "
        "Use get_tags, then generate_triples, then build_obsidian_note, then "
        "generate_semantic_graph."
    ),
    "ex_conversation_ontology": (
        "Analyze this conversation excerpt as an ontology:\n\n"
        "**Alice:** Good morning, Professor. Could you review my thesis draft?\n\n"
        "**Professor:** Of course, Alice. I'll have comments by Friday.\n\n"
        "**Alice:** Thank you so much! I was worried about the methodology section.\n\n"
        "**Professor:** The statistical approach looks sound. Just expand the "
        "literature review.\n\n"
        "Use the full tool chain: get_tags on each utterance, "
        "analyze_conversation for the dialogue structure, generate_triples "
        "for the entities and relations, build_obsidian_note for the knowledge "
        "graph, and generate_semantic_graph for visualization."
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
# Prompt builder
# ═══════════════════════════════════════════════════════════════════════════════


def build_analysis_prompt(text: str) -> str:
    """Wrap raw text in a prompt that instructs the agent to run the full
    ontological tool chain."""
    return textwrap.dedent(f"""
    Perform a full ontological analysis on the following text.

    Use the complete tool chain:
    1. Call get_tags on the text to extract tokens, entities, dependencies, and noun chunks.
    2. If the text contains conversational turns (speaker labels like **Name:**), call analyze_conversation with the utterances.
    3. Call generate_triples with the entities and relations you extracted.
    4. Call build_obsidian_note to persist the ontology as an Obsidian note with [[wikilinks]].
    5. Call generate_semantic_graph to create an interactive network visualization.

    Text to analyze:
    ---
    {text}
    ---

    When finished, return a JSON summary of what you built.
    """).strip()
