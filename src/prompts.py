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
    "You are a laconic linguistic ontologist. Your sole purpose is to map "
    "conversational text to structured ontologies using specialized tools. "
    "Do not narrate your process or comment on tool outputs and do not "
    "create any visualizations unless you are specifically asked to do so. "
    "Follow this execution logic: "
    "1. Linguistic Analysis: Call for POS tagging, NER, and syntax visualization. "
    "2. Storage: Save all findings as .md files in the 'output' folder using "
    "the file management tool. "
    "If requested to analyze and save, you must chain these tools: execute "
    "the analysis first, then pass the raw data to the write tool immediately. "
    "When saving files, always use the 'write_file' tool with the 'filename' "
    "and 'content' parameters exactly as defined in the schema. "
    "RDF Generation Rules: "
    "3. Use CURIE prefixes (ex:, rdf:, rdfs:, prov:, ibis:, aif:, skos:, schema:) "
    "for subjects and predicates — never bare strings. "
    "4. Assign rdf:type and rdfs:label to every entity. "
    "5. Tag literal objects with datatypes (xsd:string, xsd:dateTime, xsd:float). "
    "6. Use 'subject_type' and 'object_type' to mark each term as 'uri', "
    "'entity_id', 'blank_node', or 'literal'. "
    "Coreference & Entity Merging: "
    "7. MERGE co-referential mentions (e.g. 'Dr. Chen' and 'the professor') "
    "into a SINGLE canonical entity ID (ex:Dr_Chen). "
    "8. NEVER create separate nodes for titles or roles. Represent roles as "
    "properties: schema:jobTitle, ex:hasRole. "
    "Agent Binding to Reified Events: "
    "9. When generating a prov:Activity node (e.g. ex:PresentationEvent_1), "
    "ALWAYS link the agent via prov:wasAssociatedWith or schema:performer. "
    "10. Attach location and time via prov:atLocation and prov:startedAtTime. "
    "IBIS / AIF Speech Act Primitives: "
    "11. Model CLAIMS made in indirect speech ('X argued that Y') as "
    "ibis:Position or aif:I-node with the full proposition text as rdfs:label. "
    "12. Link the speaker to the claim via ibis:asserts or prov:wasAttributedTo. "
    "Example: ex:Dr_Chen ibis:asserts ex:Claim_ML_Detect_Bias . "
    "ex:Claim_ML_Detect_Bias a ibis:Position, aif:I-node ; "
    "rdfs:label 'Machine learning models can detect bias' ."
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
    "ex_maya": (
        "Analyze the following text and create a report on the dialogue: "
        "'Maya: Hi there! How are you doing today? \n"
        "Patrick: I'm doing well, thanks for asking! How about you? \n"
        "Maya: I'm great, just enjoying the weather. \n"
        "Patrick: That's good to hear. Do you have any plans for the weekend? \n"
        "Maya: Not yet, but I'm thinking of going hiking. What about you? \n"
        "Patrick: I might go to the beach if the weather stays nice. \n"
        "Maya: That sounds fun! Maybe we can go together. \n"
        "Patrick: I'd love that! Let's plan for it.'"
    ),
    "ex_maya_visualization": (
        "Analyze the following text and create a report on the dialogue: "
        "'Maya: Hi there! How are you doing today? \n"
        "Patrick: I'm doing well, thanks for asking! How about you? \n"
        "Maya: I'm great, just enjoying the weather. \n"
        "Patrick: That's good to hear. Do you have any plans for the weekend? \n"
        "Maya: Not yet, but I'm thinking of going hiking. What about you? \n"
        "Patrick: I might go to the beach if the weather stays nice. \n"
        "Maya: That sounds fun! Maybe we can go together. \n"
        "Patrick: I'd love that! Let's plan for it.', "
        "create a visualization of the analysis."
    ),
    "ex_maya_file": (
        "Analyze the following text and create a report on the dialogue: "
        "'Maya: Hi there! How are you doing today? \n"
        "Patrick: I'm doing well, thanks for asking! How about you? \n"
        "Maya: I'm great, just enjoying the weather. \n"
        "Patrick: That's good to hear. Do you have any plans for the weekend? \n"
        "Maya: Not yet, but I'm thinking of going hiking. What about you? \n"
        "Patrick: I might go to the beach if the weather stays nice. \n"
        "Maya: That sounds fun! Maybe we can go together. \n"
        "Patrick: I'd love that! Let's plan for it.', "
        "write the report to a markdown file named 'report.md'."
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
