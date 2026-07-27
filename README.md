---
title: Agentic Linguistic Analysis & Semantic Graphs
emoji: 🕸️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.20.0
python_version: "3.10"
app_file: app.py
fullWidth: true
header: mini
short_description: Agentic pipeline converting raw discourse into RDF graphs and Obsidian vaults via DeepSeek.
tags:
  - nlp
  - knowledge-graph
  - rdf
  - deepseek
  - digital-humanities
disable_embedding: false
pinned: false
---

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

# 5. Launch the Gradio Web UI
python app.py                  # http://localhost:7860
python app.py --share          # public link for embedding

# 6. See all CLI options
python run_pipeline.py --help
```

---

## Gradio Web UI

Launch `python app.py` for an interactive dashboard with:

- **Text input** + pre-loaded example selector
- **Dynamic tool checkboxes** — enable/disable Linguistic Parsing, RDF Triples, Semantic Graphs, Obsidian Notes, Conversation Analysis, and Dependency Viz
- **Tabbed output**: JSON summary, Turtle RDF, interactive semantic graph HTML, and Obsidian markdown preview
- Designed for **iframe embedding** in GitHub Pages (`kokorikos212.github.io`)

---

## Project Structure

```text
.
├── run_pipeline.py                 # 🚀 CLI entry point — pass text, get an ontology
├── app.py                          # 🖥️ Gradio Web UI — interactive dashboard
├── .env.example                    # API key template (copy to .env)
├── requirements.txt                # Core dependencies (lightweight)
├── requirements-dev.txt            # Full research stack (Convokit, PyTorch)
├── README.md
├── citations.md                    # Academic references
│
├── src/                            # Core pipeline package
│   ├── config.py                   # Centralized Config dataclass
│   ├── pipeline.py                 # DeepSeek tool-calling loop
│   ├── schemas.py                  # Pydantic output schema (OntologicalAnalysis)
│   ├── prompts.py                  # System prompt + named prompt templates
│   ├── cli.py                      # CLI argument parsing
│   └── tools/
│       ├── __init__.py             # Tool registry + filter_tool_definitions()
│       ├── linguistics.py          # spaCy POS/NER/dep + displaCy SVG
│       ├── writer.py               # Folder-restricted .md file writer
│       ├── triples.py              # RDF triple generation (rdflib)
│       ├── conversation.py         # Conversation analysis (Convokit + ad-hoc)
│       ├── obsidian.py             # Obsidian markdown notes with [[wikilinks]]
│       ├── graph.py                # networkx + pyvis semantic networks
│       └── utils.py                # Shared metadata helpers
│
├── tests/                          # Test suite (57 tests, all offline)
│   ├── test_config.py
│   ├── test_tools.py
│   ├── test_pipeline.py
│   └── test_app.py
│
├── data/                           # Convokit corpora (gitignored)
│   ├── example_article.txt
│   └── example_convo.txt
│
├── output/                         # Generated artifacts (gitignored)
│   ├── graphs/                     # SVG + interactive HTML visualizations
│   ├── rdf/                        # Turtle RDF serializations
│   ├── conversations/              # Conversation analysis JSON
│   └── verse/                      # Obsidian vault with [[wikilinks]]
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

The pipeline produces an `OntologicalAnalysis` (see `src/schemas.py`):

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

Open `output/verse/` as an Obsidian vault to browse the extracted knowledge graph interactively.

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
# Place conversation-gone-awry-corpus/ and winning-args-corpus/ under data/
```

---

## Security

- The `.env` file (containing `DEEPSEEK_KEY`) is **gitignored** — never commit it.
- If you previously committed a key, **rotate it** at [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys).
