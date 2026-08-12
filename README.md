---
title: Talos Agentic Discourse Analysis Engine
emoji: 🕸️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.1
python_version: "3.10"
app_file: app.py
fullWidth: true
header: mini
short_description: Discourse to RDF graphs, statistics, and Obsidian vaults
tags:
  - nlp
  - knowledge-graph
  - rdf
  - deepseek
  - digital-humanities
  - computational-social-science
disable_embedding: false
pinned: false
---

# 🏛️ Talos: Agentic Discourse Extraction Engine for Democratic Deliberation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/UI-Gradio%204.44.1-orange.svg)](app.py)
[![RDF Standards](https://img.shields.io/badge/RDF-W3C%20Compliant-green.svg)](https://www.w3.org/TR/prov-o/)

An interdisciplinary framework integrating **Computational Social Science**, **Linguistic Statistics**, **Semantic Web Technologies (RDF/OWL)**, and **Agentic LLM Workflows**. **Talos** translates unstructured deliberative text—such as student assembly minutes, parliamentary debates, and structured notes—into deterministic, fully-connected RDF knowledge graphs $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{L})$, interactive PyVis networks, statistical divergence reports, and Obsidian knowledge vaults.

---

## 🌟 Key Features

* **Multi-Tenant Sandboxed Workspaces:** Complete user registration, login authentication, and project isolation (`data/users/{uid}/projects/{pid}/`) ensuring secure data handling and persistent session state.
* **Micro-Ontology Synthesis Stack:** Combines **IBIS**, **AIF**, **SKOS**, **PROV-O**, and **Schema.org** to eliminate custom ontology silos and represent complex discourse topologies.
* **Context-Agnostic Vocabulary Engine:**
  * *Single Text Analysis:* Auto-populates from workspace text (or manual `.txt`/`.md` file uploads) and splits corpus halves to isolate internal term imbalances via Weighted Log-Odds ($z$-scores) with uninformative Dirichlet priors.
  * *Comparative Corpus Analysis:* Ingests dual text corpora to calculate Jensen-Shannon Divergence ($JSD \in [0, 1]$), Pearson's Chi-Square ($\chi^2$) independence test ($p$-value), Vector Cosine Similarity, and discriminative term tables.
* **Five Deterministic Pipeline Invariants:** Automated post-processing guarantees 100% single-component graph connectivity, speech-act noise filtering, typed edge directionality, label abstraction, and canonical URI resolution.
* **Pre-Computed Benchmark Suite & Interactive SPARQL Runner:** Instant loading of verified case study graphs with an in-browser SPARQL query execution suite for thesis metrics (Node Divergence $D_{\text{nd}}$ and Hub Centrality $W_{\text{hub}}$).
* **Embedded PTY Linux Terminal & File Manager:** Web-based `xterm.js` terminal over WebSockets with a file tree browser, direct upload/zip-download capabilities, and CLI batch tools (`src/cli/analyze_factions.py`).
* **Interactive Talos Graph Viewer:** Client-side graph physics visualization with node filtering, freeze-canvas controls, wildcard searching, and live node deletion.

---

## 🏗️ System Architecture

```text
                                 [ User Input / Assembly Text ]
                                               │
                                               ▼
                                   ┌───────────────────────┐
                                   │  src/pipeline.py      │
                                   │  DeepSeek Agent Loop  │
                                   └───────────┬───────────┘
                                               │ Dynamic Output Checkboxes
                                               ▼
     ┌──────────────────────────────────────────────────────────────────────────────────┐
     │                             src/tools/ Registry                                  │
     ├───────────────┬───────────────────────┬───────────────┬──────────────────────────┤
     │  linguistics  │       triples         │   obsidian    │        statistics        │
     │ (spaCy POS/   │ (RDFLib Multi-Graph   │ (Markdown     │ (Monroe Dirichlet        │
     │  NER/dep)     │  + Invariants I-V)    │  Wikilinks)   │  Log-Odds, JSD, Chi-Sq)  │
     └───────────────┴───────────┬───────────┴───────────────┴──────────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Talos Graph Viewer  │
                     │ (PyVis HTML Network)  │
                     └───────────────────────┘
```

---

## 🌐 Micro-Ontology Synthesis Stack

Talos maps natural language arguments across five established open standards:

| Ontology | Namespace URI | Core Classes / Predicates | System Mapping Scope |
|----------|--------------|---------------------------|---------------------|
| **IBIS** | `http://purl.org/ibis#` | `ibis:Issue`, `ibis:Position`, `ibis:rebuts` | Deliberative friction, questions, stances, counter-arguments |
| **AIF** | `http://www.arg.tech/aif#` | `aif:I-node`, `aif:conflicts`, `aif:supports` | Formal argument schemes, claim reification, edge links |
| **SKOS** | `http://www.w3.org/2004/02/skos/core#` | `skos:Concept`, `skos:related` | Institutional hub concepts, Mental-Tool taxonomies |
| **PROV-O** | `http://www.w3.org/ns/prov#` | `prov:Activity`, `prov:wasAssociatedWith` | Reified speech events, provenance, agent attribution |
| **Schema.org** | `http://schema.org/` | `schema:Person`, `schema:Organization`, `schema:about` | Real-world entities, job titles, metadata, aboutness links |

---

## ⚙️ Deterministic Pipeline Invariants

To guarantee valid, computable multi-graphs without floating entities or label clutter, the backend enforces five strict invariants:

1. **Entity Binding Invariant** (`_bind_isolated_nodes`): Any degree-0 entity extracted is automatically bound to the primary `ibis:Issue` node via `schema:about`, guaranteeing 100% connected single-component graphs.
2. **Speech-Act Noise Filter**: Phatic turns, polite chatter, and administrative scheduling are discarded at extraction time, restricting `ibis:Position` nodes to empirical/normative claims.
3. **Typed Edge Directionality**: Rebuttals emit `ibis:rebuts`, partial concessions emit `aif:supports`, and compromise proposals emit `ibis:reframes`.
4. **Concise Label Abstraction**: Restricts `rdfs:label` strings to 3–7 words, placing unabridged verbatim text into literal `aif:claimText` or `schema:text` nodes.
5. **Canonical URI Normalization**: Resolves surface-form entity variations to unified URIs prior to graph instantiation, eliminating node duplication.

---

## 📂 Repository Structure

```text
Digital_Humanities/
├── app.py                      # Stage-driven Gradio UI & FastAPI app server
├── run_pipeline.py             # CLI entry point for batch graph processing
├── requirements.txt            # Lightweight production dependencies
├── assets/
│   └── precomputed/            # Benchmark case assets (.ttl, .html, .md, .json)
├── data/
│   └── users/                  # Multi-tenant user project sandboxes
│       └── {uid}/projects/{pid}/
│           ├── documents/      # Raw uploaded texts and transcripts
│           ├── notes/          # Generated Obsidian Markdown vault
│           └── graph.ttl       # Project RDF Knowledge Graph
└── src/
    ├── config.py               # Dataclass configuration & environment loader
    ├── ingestion.py            # Sandboxed file ingestion & user directory resolver
    ├── pipeline.py             # Core LLM tool-calling orchestration engine
    ├── prompts.py              # Invariant extraction prompts & System instructions
    ├── queries.py              # Case-aware SPARQL query benchmark registry
    ├── schemas.py              # Pydantic v2 schemas (OntologicalAnalysis, MentalTool)
    ├── analytics/
    │   └── health_diagnostics.py # Microdemocratic health metrics & path analysis
    ├── cli/
    │   ├── analyze_factions.py # CLI batch vocabulary divergence engine
    │   └── metrics.py          # Standalone CLI metrics wrapper
    └── tools/                  # Modular tool suite
        ├── file_manager.py     # File tree browser, zip packager, and downloader
        ├── graph.py            # PyVis interactive network visualization generator
        ├── linguistics.py      # spaCy NLP (POS, NER, Dependency Trees)
        ├── obsidian.py         # Obsidian Markdown vault builder
        ├── semantics.py        # Micro-ontology mapping layer (IBIS/AIF/SKOS)
        ├── statistics.py       # Dirichlet Log-Odds, JSD, Chi-Square engine
        ├── terminal.py         # Sandboxed bash terminal engine
        ├── triples.py          # RDFLib triple generator & Invariant binder
        └── writer.py           # Path-restricted file persistence agent
```

---

## 🚀 Quickstart & Setup

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/kokorikos212/Digital_Humanities.git
cd Digital_Humanities

# Create virtual environment & activate
python3 -m venv venv
source venv/bin/activate

# Install dependencies and download spaCy model
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
DEEPSEEK_KEY=sk-your-deepseek-api-key-here
```

### 3. Running the Web Application

Launch the interactive web portal (Auth → Project Dashboard → Workspace):

```bash
python3 app.py
```

Access the interface locally at `http://localhost:7860`.

### 4. CLI Batch Execution

**A. Graph Extraction Pipeline** — Process a local text file directly via the command line:

```bash
python run_pipeline.py --input data/example_convo.txt --output-dir output/
```

**B. Terminal Batch Statistical Divergence Analysis** — Analyze two document directories:

```bash
python -m src.cli.analyze_factions \
    --dir-a data/users/default/projects/demo/factions/faction_a \
    --dir-b data/users/default/projects/demo/factions/faction_b \
    --out-dir analysis_results
```

---

## 📊 Benchmark SPARQL Queries & Thesis Metrics

Talos enables direct computation of computational social choice metrics using SPARQL queries over generated `.ttl` outputs.

### Node Divergence ($D_{\text{nd}}$) Baseline Query

Extracts opposing positions and asserted sub-triples across student council factions to compute semantic distance:

```sparql
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX aif:    <http://www.arg.tech/aif#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?issueLabel ?faction1 ?pos1Label ?pos2Label
WHERE {
  ?issue a ibis:Issue ;
         rdfs:label ?issueLabel .

  ?pos1 ibis:respondsTo ?issue ;
        prov:wasAttributedTo ?faction1 ;
        rdfs:label ?pos1Label ;
        ibis:rebuts ?pos2 .

  ?pos2 ibis:respondsTo ?issue ;
        rdfs:label ?pos2Label .
}
```

### Hub-Node Centrality ($W_{\text{hub}}$) SKOS Query

Calculates network centrality over institutional and moral concepts:

```sparql
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?conceptLabel (COUNT(?connectedNode) AS ?degreeCentrality)
WHERE {
  ?concept a skos:Concept ;
           rdfs:label ?conceptLabel .

  { ?concept ?p ?connectedNode . }
  UNION
  { ?connectedNode ?p2 ?concept . }
}
GROUP BY ?concept ?conceptLabel
ORDER BY DESC(?degreeCentrality)
```

---

## 🎓 Academic Context & Citation

Developed as part of the Digital Humanities Minor (Talos Project) at the University of Crete and presented at the **Semantic Annotation for the Ancient World (SAW 2026)** conference in Rethymno, Crete.

```bibtex
@article{talos2026discourse,
  title={Talos: An Agentic Discourse Extraction Engine for Democratic Deliberation via Micro-Ontology Synthesis},
  author={Department of Applied Mathematics \& Digital Humanities},
  institution={University of Crete},
  year={2026}
}
```

---

## 📄 License

Distributed under the MIT License.
