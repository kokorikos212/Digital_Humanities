# Digital Humanities: Agentic Ontological Discourse Analysis

An interdisciplinary framework integrating **Computational Linguistics**, **Knowledge Representation (RDF/OWL)**, and **Agentic LLM Workflows** to extract structured ontologies from conversational text and visualize discourse as interactive knowledge graphs.

---

## Overview

This project empowers an LLM with a suite of linguistic and knowledge-graph tools. Given a text or conversation, the agent autonomously:

1. **Parses** — POS tagging, dependency parsing, named entity recognition (spaCy)
2. **Structurizes** — Speaker turns, reply chains, pragmatic features (Convokit)
3. **Ontologizes** — Extracts entities and relations into RDF triples (rdflib)
4. **Visualizes** — Renders dependency trees, entity displays, and interactive semantic networks (pyvis)
5. **Persists** — Writes Obsidian-compatible markdown notes with YAML frontmatter and `[[wikilinks]]` for graph browsing

The final output is an `OntologicalAnalysis` — a structured JSON envelope containing entities, RDF triples, visualization paths, and Obsidian note references.

---

## Quickstart

```bash
# 1. Clone and set up
git clone <repo-url>
cd Digital_Humanities
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Add your API key
cp .env.example .env
# Edit .env and paste your DeepSeek key

# 3. Run the pipeline
python run_pipeline.py --text "Dr. Chen presented the research at Stanford University."

# 4. Or analyze a conversation
python run_pipeline.py --text "Alice: Hello Professor! Could you review my thesis?
Bob: Of course, Alice. I'll have comments by Friday."

# 5. See all options
python run_pipeline.py --help
```

---

## Project Structure

```text
.
├── run_pipeline.py                 # 🚀 Entry point — pass text, get an ontology
├── .env.example                    # API key template (copy to .env)
├── requirements.txt                # Python dependencies
├── README.md
├── citations.md                    # Academic references
│
├── agent/                          # Core agent environment
│   ├── agent.py                    # DeepSeek tool-calling loop
│   ├── schemas.py                  # Pydantic output schema (OntologicalAnalysis, …)
│   ├── database/
│   │   ├── system_prompt.json      # LLM persona ("laconic linguistic ontologist")
│   │   └── prompts.json            # Example prompts
│   ├── tools/
│   │   ├── __init__.py             # Tool registration & handler mapping
│   │   ├── toolset.py              # linguisticTools: spaCy POS/NER/dep/Viz
│   │   ├── tools_to_write.py       # FolderRestrictedAgent: safe .md writer
│   │   ├── triple_generator.py     # TripleGenerator: entities → RDF triples
│   │   ├── conversation_analyzer.py# ConversationAnalyzer: Convokit + pragmatics
│   │   ├── obsidian_builder.py     # ObsidianBuilder: YAML frontmatter + [[wikilinks]]
│   │   ├── graph_builder.py        # GraphBuilder: networkx + pyvis semantic net
│   │   └── utils.py                # Shared metadata helpers
│   └── data/                       # Convokit corpora (gitignored — large files)
│
└── resources/
    └── poster.pdf                  # Conference poster (SAW 2026, Rethymno)
```

---

## Tools — What the Agent Can Do

| # | Tool | What It Produces |
|---|------|-----------------|
| 1 | `get_tags` | Tokens, POS tags, lemmas, dependencies, NER, noun chunks |
| 2 | `generate_viz` | displaCy SVG dependency tree or entity display |
| 3 | `analyze_conversation` | Speaker structure, reply graph, pragmatics (politeness, toxicity, dialogue acts) |
| 4 | `generate_triples` | RDF triples (Turtle/JSON-LD) from entities + relations |
| 5 | `build_obsidian_note` | `.md` file with YAML frontmatter and `[[wikilinks]]` for Obsidian's graph view |
| 6 | `generate_semantic_graph` | Interactive pyvis HTML semantic network (nodes = entities, edges = relations) |
| 7 | `write_file` | Plain markdown report |

The agent chains these tools autonomously — the system prompt gives it a strict execution order.

---

## Output Schema

The pipeline produces an `OntologicalAnalysis` (see `agent/schemas.py`):

```
OntologicalAnalysis
├── analysis_id, source_text, source_corpus
├── linguistic_analysis  →  tokens, entities, dependencies, noun_chunks
├── conversation         →  speakers, utterances, reply_graph, pragmatics
├── ontology             →  entities (rdf:type + properties), triples, prefixes
├── obsidian_notes       →  generated .md files with [[wikilinks]]
├── visualizations       →  paths to SVG / HTML artifacts
└── summary              →  human-readable narrative
```

Open `agent/output/verse/` as an Obsidian vault to browse the extracted knowledge graph interactively.

---

## Conference

Presented at **"Semantic Annotation for the Ancient World"** (Rethymno, Crete, 2026).

- **Affiliation:** Digital Humanities Minor, Talos — University of Crete
- **Topic:** Argument Modeling with Agentic Workflows
- **Conference site:** [SAW 2026](https://talos-ai4ssh.uoc.gr/events/conferences/semantic-annotation-for-the-ancient-world-conference-2026/)

📄 **[View the Research Poster (PDF)](resources/poster.pdf)**

---

## Setup for Development

```bash
# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Download Convokit corpora (optional — for conversation analysis)
# Place conversation-gone-awry-corpus/ and winning-args-corpus/ under agent/data/
```

---

## Security

- The `.env` file (containing `DEEPSEEK_KEY`) is **gitignored** — never commit it.
- If you previously committed a key, **rotate it** at [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys).
- The legacy `agent/database/envariables.json` is also gitignored; use `.env` instead.
