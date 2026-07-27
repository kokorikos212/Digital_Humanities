---
title: Agentic Linguistic Analysis & Semantic Graphs
emoji: 🕸️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.1
python_version: "3.10"
app_file: app.py
fullWidth: true
header: mini
short_description: Discourse to RDF graphs and Obsidian vaults via DeepSeek
tags:
  - nlp
  - knowledge-graph
  - rdf
  - deepseek
  - digital-humanities
disable_embedding: false
pinned: false
---

# Agentic Ontological Discourse Analysis

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Gradio UI](https://img.shields.io/badge/Gradio-Live_Demo-orange.svg?style=flat-square)](https://nospadiss-agentic-linguistic-analysis.hf.space)
[![RDF/OWL](https://img.shields.io/badge/Ontology-RDF%2FTurtle-blue.svg?style=flat-square)](https://www.w3.org/TR/turtle/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

An interdisciplinary framework bridging **Computational Linguistics**, **Knowledge Representation (RDF/OWL)**, and **Agentic LLM Workflows**. The pipeline autonomously extracts structured semantic networks from natural language text and serializes discourse into interactive knowledge graphs and Obsidian graph vaults.

Originally presented at the **Semantic Annotation for the Ancient World (SAW 2026)** conference at the University of Crete.

[**Live Interactive Demo**](https://nospadiss-agentic-linguistic-analysis.hf.space) &nbsp;|&nbsp; [**GitHub Pages Portfolio**](https://kokorikos212.github.io/Digital_Humanities/) &nbsp;|&nbsp; [**Research Poster (PDF)**](resources/poster.pdf)

---

## Architectural Workflow

```text
               +-------------------------------------------------------+
               |                  Unstructured Text                    |
               +---------------------------+---------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |              DeepSeek Agent Orchestrator             |
               +---------------------------+---------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                       |                       |
                   v                       v                       v
        +---------------------+ +---------------------+ +---------------------+
        |  Linguistic Tool    | |   RDF Serializer    | | Pyvis Network Graph |
        |  (spaCy POS/NER)    | |  (rdflib Turtle)    | |  (Interactive HTML) |
        +----------+----------+ +----------+----------+ +----------+----------+
                   |                       |                       |
                   +-----------------------+-----------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |        Obsidian Vault Node Generation ([[links]])    |
               +-------------------------------------------------------+
```

## Technical Highlights

- **Dynamic Tool Gating:** The agent toolset is conditionally initialized at runtime based on user selection, preventing redundant computation during API execution.
- **Formal Semantic Serialization:** Generates valid RDF/Turtle triples with predefined namespaces (`owl:`, `rdf:`, `rdfs:`, custom domain ontologies).
- **Obsidian Graph Integration:** Generates `.md` notes complete with YAML frontmatter metadata and `[[wikilinks]]` for direct graph visualization inside Obsidian.
- **Deterministic Output Contract:** Employs Pydantic schemas (`OntologicalAnalysis`) to guarantee structured outputs across agent execution cycles.

## Tool Dispatch Registry

The agent autonomously orchestrates execution across a modular tool suite:

| Component | Class / Module | Primary Responsibility | Target Output |
|-----------|---------------|----------------------|---------------|
| Linguistics | `LinguisticTools` | POS tagging, dependency trees, NER, noun chunks | Struct Dict / SVG render |
| Triples Engine | `TripleGenerator` | Entity-relation extraction & RDF predicate binding | Turtle (.ttl) / JSON-LD |
| Graph Visualizer | `GraphBuilder` | Semantic network construction & layout physics | Pyvis HTML network |
| Vault Engine | `ObsidianBuilder` | Structured Markdown page generation with graph linkages | .md with [[wikilinks]] |
| Conversation | `ConversationAnalyzer` | Utterance structure, pragmatic attributes, reply graphs | Structural JSON |
| File Dispatch | `FolderRestrictedAgent` | Safe file persistence within project boundaries | Markdown reports |

## Quickstart & Local Setup

### 1. Environment Configuration

```bash
# Clone repository
git clone https://github.com/kokorikos212/Digital_Humanities.git
cd Digital_Humanities

# Virtual environment & lightweight core install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### 2. API Key Provisioning

```bash
cp .env.example .env
# Open .env and populate DEEPSEEK_KEY=sk-...
```

### 3. CLI Execution

```bash
# Analyze a single statement
python run_pipeline.py --text "Dr. Chen presented the research at Stanford University."

# Analyze a conversational exchange
python run_pipeline.py --text "Alice: Could you review my thesis?
Bob: Of course, Alice. I'll have comments by Friday."
```

### 4. Interactive Web Interface

```bash
# Launch local Gradio dashboard
python app.py
```

## Project Structure

```text
.
├── app.py                     # Gradio UI application entry point
├── run_pipeline.py            # CLI entry point wrapper
├── requirements.txt           # Core lightweight deployment dependencies
├── requirements-dev.txt       # Full research stack (Convokit, PyTorch)
├── src/                       # Package core
│   ├── config.py              # Centralized environment & path resolver
│   ├── pipeline.py            # Agent orchestration & tool execution loop
│   ├── schemas.py             # Pydantic data contracts
│   ├── prompts.py             # System prompt definitions & templates
│   ├── cli.py                 # CLI argument parsing
│   └── tools/                 # Tool implementations
│       ├── linguistics.py     # spaCy & displaCy integration
│       ├── triples.py         # rdflib Turtle generation
│       ├── graph.py           # pyvis network visualizer
│       ├── obsidian.py        # Obsidian vault writer
│       ├── conversation.py    # Discourse structure analyzer
│       └── writer.py          # Sandboxed file persistence
├── tests/                     # Offline test suite (pytest)
└── docs/                      # GitHub Pages landing site & integration notes
```

## Academic Context & Citation

Developed as part of the Digital Humanities Minor (Talos Project) at the University of Crete and presented at the **Semantic Annotation for the Ancient World (SAW 2026)** conference in Rethymno, Crete.

```bibtex
@inproceedings{mavroudis2026agentic,
  title={Argument Modeling with Agentic Workflows for Discourse Analysis},
  author={Mavroudis, Panagiotis},
  booktitle={Semantic Annotation for the Ancient World (SAW 2026)},
  year={2026},
  organization={University of Crete & Talos AI4SSH}
}
```

## License

Distributed under the MIT License.
