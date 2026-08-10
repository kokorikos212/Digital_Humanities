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
    "rdfs:label 'Machine learning models can detect bias' . "
    "Temporal & Prefix Consistency: "
    "13. Compute relative dates ('last Tuesday', 'yesterday') dynamically "
    "relative to the CURRENT date — NEVER use hardcoded placeholder dates. "
    "14. Decompose complex claims into sub-triples when queryability matters: "
    "ex:ML_Models ex:detects ex:Bias . ex:Bias ex:foundIn ex:Political_Speeches . "
    "Link sub-triples to the ibis:Position node via aif:claimText. "
    "15. EVERY rdf:type value MUST use a CURIE prefix (prov:Activity, "
    "ibis:Position, schema:Person, xsd:dateTime). NEVER emit bare types "
    "like 'Activity' or 'Position' without their namespace prefix."
)

from datetime import date as _today


def get_system_prompt() -> str:
    """Return the system prompt with the current date injected for temporal
    normalization (rule 13)."""
    return f"Today is {_today.today().isoformat()}. " + SYSTEM_PROMPT


# ═══════════════════════════════════════════════════════════════════════════════
# Named prompt templates
# ═══════════════════════════════════════════════════════════════════════════════

NAMED_PROMPTS: Dict[str, str] = {
    # ── Baseline: simple Dr. Chen ontology (kept for quick smoke tests) ──
    "ex_ontology_basic": (
        "Perform a full ontological analysis on this text: "
        "'Dr. Chen presented the research findings at Stanford University "
        "last Tuesday. The professor argued that machine learning models can "
        "detect bias in political speeches.' "
        "Use get_tags, then generate_triples, then build_obsidian_note, then "
        "generate_semantic_graph."
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Category 1 — Multi-Turn Rebuttal & Conflict Topology
    # ═══════════════════════════════════════════════════════════════════════

    "bench_1_1_rebuttal": (
        "Perform a full ontological analysis on this debate, extracting "
        "ibis:Issue, ibis:Position, and ibis:rebuts / aif:conflicts edges:\n\n"
        "Moderator: Should the university allocate the surplus budget to lab "
        "equipment or student housing subsidies?\n\n"
        "Representative Alex: We must prioritize lab equipment. Modernizing "
        "our computing labs directly impacts academic output and research "
        "rankings.\n\n"
        "Representative Maria: I disagree strongly. Computing labs are "
        "functional, but 40% of our student body faces severe housing "
        "insecurity. Housing subsidies must come first."
    ),

    "bench_1_2_escalation": (
        "Perform a full ontological analysis on this multi-party debate, "
        "extracting cross-claim conflict edges and resolution proposals:\n\n"
        "Chairman: The proposed amendment suggests mandatory attendance for "
        "all departmental assemblies.\n\n"
        "Faction A: Mandatory attendance ensures full democratic "
        "representation and eliminates illegitimate minority votes.\n\n"
        "Faction B: That argument is flawed. Forcing attendance creates "
        "artificial participation without genuine engagement and penalizes "
        "working students.\n\n"
        "Faction C: Faction B is right about working students, but we can "
        "resolve this by introducing asynchronous digital voting instead."
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Category 2 — Conversational Noise vs. Actionable Claims
    # ═══════════════════════════════════════════════════════════════════════

    "bench_2_1_noise": (
        "Analyze this committee dialogue and extract ONLY actionable "
        "ibis:Position nodes — do NOT create entity nodes for polite turns "
        "or emotional statements:\n\n"
        "Alice: Good afternoon, everyone. Thanks for making time on a "
        "Friday.\n\n"
        "Bob: Happy to be here, though I'm exhausted from midterms!\n\n"
        "Alice: I feel you. Anyway, I move that we publish assembly voting "
        "records publicly on the department portal.\n\n"
        "Bob: Sounds good to me. I was worried students wouldn't care, but "
        "transparency is vital for institutional trust.\n\n"
        "Alice: Great, let's submit the motion before 5 PM."
    ),

    "bench_2_2_mixed": (
        "Analyze this procedural dialogue. Extract policy claims but do NOT "
        "reify procedural noise (lateness, small talk) into ontology nodes:\n\n"
        "Elena: Sorry I'm late, the bus was delayed. Did I miss the vote on "
        "the library hours?\n\n"
        "Dimitris: No worries, Elena. We just started. Faction X proposed "
        "extending the library to 24/7 during exam periods.\n\n"
        "Elena: Oh, fantastic! I was really stressed about finding quiet "
        "study space after midnight."
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Category 3 — Complex Coreference & Role Attribute Resolution
    # ═══════════════════════════════════════════════════════════════════════

    "bench_3_1_multi_title": (
        "Analyze this report. Merge all mentions of the same individual "
        "into a SINGLE canonical node with role properties. Do NOT create "
        "duplicate Person nodes:\n\n"
        "Dean Varga announced the new research grant during Monday's faculty "
        "senate meeting. The head of the computer science department "
        "emphasized that the funding will support three doctoral fellowships. "
        "Varga noted that applications open next month."
    ),

    "bench_3_2_pronoun": (
        "Analyze this text. Resolve pronominal coreference (she → Sarah "
        "Jenkins) into ONE canonical person node. Extract the claim as an "
        "ibis:Position:\n\n"
        "President Sarah Jenkins addressed the student assembly on Tuesday "
        "regarding tuition freezes. The student council leader argued that "
        "rising living costs make fee increases unacceptable. She urged the "
        "board to vote against the proposal."
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Category 4 — Dynamic Temporal & Event Reification
    # ═══════════════════════════════════════════════════════════════════════

    "bench_4_1_relative_dates": (
        "Analyze this text. Compute ALL relative dates dynamically relative "
        "to today (do NOT use placeholder dates). Use xsd:dateTime typed "
        "literals:\n\n"
        "Professor Papadopoulos submitted the revised curriculum proposal "
        "last Wednesday. The departmental board scheduled the formal vote "
        "for next Friday, while student feedback will remain open until "
        "two days before the vote."
    ),

    "bench_4_2_nested_temporal": (
        "Analyze this text. Reify each temporal event as a prov:Activity "
        "with prov:startedAtTime. Compute all relative dates dynamically:\n\n"
        "Three days ago, Faction A published its election manifesto. The "
        "student union hosted a public debate yesterday evening, and the "
        "final election will take place this coming Thursday at 9:00 AM."
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Category 5 — Complex Claim Decomposition & Nested Modality
    # ═══════════════════════════════════════════════════════════════════════

    "bench_5_1_modal": (
        "Analyze this policy claim. Preserve modal operators ('could', "
        "'reduce by 50%') in the ibis:Position label. Optionally decompose "
        "sub-triples via aif:claimText:\n\n"
        "Faction B argued that implementing an automated vote-counting "
        "system could reduce election audit times by 50% while mitigating "
        "human counting errors during late-night assemblies."
    ),

    "bench_5_2_nested_conditional": (
        "Analyze this statement. Preserve nested conditionals ('if...might "
        "...provided that') in the ibis:Position text. Reify the speaker, "
        "the claim, and any apodosis/protasis sub-components:\n\n"
        "Dr. Aris claimed that if the student union adopts digital voting "
        "delegates, assembly turnout might increase among off-campus "
        "students, provided that cryptographic anonymity is guaranteed."
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
