Markdown---
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
short_description: Discourse to RDF knowledge graphs and Obsidian vaults via DeepSeek
tags:
  - nlp
  - knowledge-graph
  - rdf
  - deepseek
  - digital-humanities
disable_embedding: false
pinned: false
---

# 🏛️ Talos: Agentic Discourse Extraction Engine for Democratic Deliberation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/UI-Gradio%204.44.1-orange.svg)](app.py)
[![RDF Standards](https://img.shields.io/badge/RDF-W3C%20Compliant-green.svg)](https://www.w3.org/TR/prov-o/)

An interdisciplinary framework integrating **Computational Social Science**, **Semantic Web Technologies (RDF/OWL)**, and **Agentic LLM Workflows**. **Talos** translates unstructured deliberative text—such as student assembly minutes, parliamentary debates, and structured notes—into deterministic, fully-connected RDF knowledge graphs $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{L})$, interactive PyVis networks, and Obsidian knowledge vaults.

---

## 🌟 Key Features

* **Multi-Tenant Sandboxed Workspaces:** Complete user registration, login authentication, and project isolation (`data/users/{uid}/projects/{pid}/`) ensuring secure data handling.
* **Micro-Ontology Synthesis Stack:** Combines **IBIS**, **AIF**, **SKOS**, **PROV-O**, and **Schema.org** to eliminate custom ontology silos and represent complex discourse topologies.
* **Deterministic Pipeline Invariants:** Five post-processing invariants guarantee 100% single-component graph connectivity, speech-act filtering, and canonical URI resolution.
* **Pre-Computed Benchmark Suite & SPARQL Engine:** Instant loading of verified case study graphs with an in-browser SPARQL query execution suite for thesis metrics (Node Divergence $D_{\text{nd}}$ and Hub Centrality $W_{\text{hub}}$).
* **Embedded PTY Linux Terminal & File Manager:** Web-based `xterm.js` terminal over WebSockets with file browser, direct upload/zip-download capabilities, and CLI tool support (including Claude Code integration).
* **Interactive Talos Viewer:** Client-side graph physics visualization with node filtering, freeze-canvas controls, wildcard searching, and live node deletion.

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
                                               │ Dynamic Tool Gating
                                               ▼
                   ┌───────────────────────────────────────────────────────┐
                   │                 src/tools/ Registry                   │
                   ├───────────────┬───────────────────────┬───────────────┤
                   │  linguistics  │       triples         │   obsidian    │
                   │ (spaCy POS/   │ (RDFLib Multi-Graph   │ (Markdown     │
                   │  NER/dep)     │  + Invariants I-V)    │  Wikilinks)   │
                   └───────────────┴───────────┬───────────┴───────────────┘
                                               │ Verified Turtle (.ttl)
                                               ▼
                                   ┌───────────────────────┐
                                   │   Talos Graph Viewer  │
                                   │ (PyVis HTML Network)  │
                                   └───────────────────────┘
🌐 Micro-Ontology Synthesis StackTalos maps natural language arguments across five established open standards:OntologyNamespace URICore Classes / PredicatesSystem Mapping ScopeIBIShttp://purl.org/ibis#ibis:Issue, ibis:Position, ibis:rebutsDeliberative friction, questions, stances, counter-argumentsAIFhttp://www.arg.tech/aif#aif:I-node, aif:conflicts, aif:supportsFormal argument schemes, claim reification, edge linksSKOShttp://www.w3.org/2004/02/skos/core#skos:Concept, skos:relatedInstitutional hub concepts, Mental-Tool taxonomiesPROV-Ohttp://www.w3.org/ns/prov#prov:Activity, prov:wasAssociatedWithReified speech events, provenance, agent attributionSchema.orghttp://schema.org/schema:Person, schema:Organization, schema:aboutReal-world entities, job titles, metadata, aboutness links⚙️ Deterministic Pipeline InvariantsTo guarantee valid, computable multi-graphs without floating entities or label clutter, the backend enforces five strict invariants:Entity Binding Invariant (_bind_isolated_nodes): Any degree-0 entity extracted is automatically bound to the primary ibis:Issue node via schema:about, guaranteeing 100% connected single-component graphs.Speech-Act Noise Filter: Phatic turns, polite chatter, and administrative scheduling are discarded at extraction time, restricting ibis:Position nodes to empirical/normative claims.Typed Edge Directionality: Rebuttals emit ibis:rebuts, partial concessions emit aif:supports, and compromise proposals emit ibis:reframes.Concise Label Abstraction: Restricts rdfs:label strings to 3–7 words, placing unabridged verbatim text into literal aif:claimText or schema:text nodes.Canonical URI Normalization: Resolves surface-form entity variations to unified URIs prior to graph instantiation, eliminating node duplication.📂 Repository StructurePlaintextDigital_Humanities/
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
    ├── cli/
    │   ├── pipeline.py         # Pipeline CLI (text → ontology)
    │   └── analyze_factions.py # Batch faction vocabulary divergence
    └── tools/                  # Modular tool suite
        ├── file_manager.py     # File tree browser, zip packager, and downloader
        ├── graph.py            # PyVis interactive network visualization generator
        ├── linguistics.py      # spaCy NLP (POS, NER, Dependency Trees)
        ├── obsidian.py         # Obsidian Markdown vault builder
        ├── statistics.py       # Log-odds ratio, JSD, chi-square divergence
        ├── terminal.py         # Sandboxed bash terminal engine
        ├── triples.py          # RDFLib triple generator & Invariant binder
        └── writer.py           # Path-restricted file persistence agent
🚀 Quickstart & Setup1. InstallationBash# Clone the repository
git clone [https://github.com/kokorikos212/Digital_Humanities.git](https://github.com/kokorikos212/Digital_Humanities.git)
cd Digital_Humanities

# Create virtual environment & activate
python3 -m venv venv
source venv/bin/activate

# Install dependencies and download spaCy model
pip install -r requirements.txt
python -m spacy download en_core_web_sm
2. Environment ConfigurationCreate a .env file in the project root:BashDEEPSEEK_KEY=sk-your-deepseek-api-key-here
3. Running the Web ApplicationLaunch the interactive web portal (Auth $\rightarrow$ Project Dashboard $\rightarrow$ Workspace):Bashpython3 app.py
Access the interface locally at http://localhost:7860.4. CLI Batch ExecutionProcess a local text file directly via the command line:Bashpython run_pipeline.py --text "Dr. Chen presented at Stanford."

---

## 💻 CLI Reference

Talos provides two CLI entry points for batch and headless workflows.

### Pipeline Analysis (`run_pipeline.py` / `src/cli/pipeline.py`)

Process a single text or file through the full ontological pipeline:

```bash
# Analyze inline text
python run_pipeline.py --text "Dr. Chen presented the research at Stanford."

# Analyze a text file
python run_pipeline.py --file data/example_convo.txt

# Use a named prompt
python run_pipeline.py --prompt bench_1_1_rebuttal

# Export the RDF graph as HTML
python run_pipeline.py --text "..." --visualize

# List all available prompts
python run_pipeline.py --list-prompts

# Full options
python run_pipeline.py --help
```

### Faction Vocabulary Divergence (`src/cli/analyze_factions.py`)

Batch-compare two directories of faction documents and export statistical reports:

```bash
# Compare faction A vs faction B corpora
python -m src.cli.analyze_factions \
  --dir-a factions/faction_a \
  --dir-b factions/faction_b \
  --out-dir analysis_results

# Customize top-N discriminative terms
python -m src.cli.analyze_factions \
  --dir-a factions/faction_a \
  --dir-b factions/faction_b \
  --top-n 25

# Outputs written to analysis_results/:
#   summary.json             — JSD, chi-square p-value, cosine similarity
#   discriminative_terms.csv — weighted log-odds z-scores
#   divergence_report.md     — executive summary in Markdown
```

**Workflow Example:**

```bash
# 1. Create faction directories and upload documents (via UI or terminal)
mkdir -p factions/faction_a factions/faction_b

# 2. Run batch analysis from the terminal
python -m src.cli.analyze_factions \
  --dir-a factions/faction_a \
  --dir-b factions/faction_b \
  --out-dir analysis_results

# 3. View results
cat analysis_results/divergence_report.md
```

---

📊 Benchmark SPARQL Queries & Thesis MetricsTalos enables direct computation of computational social choice metrics using SPARQL queries over generated .ttl outputs:Node Divergence ($D_{\text{nd}}$) Baseline QueryExtracts opposing positions and asserted sub-triples across student council factions to compute semantic distance:Code snippetPREFIX ibis:   [http://purl.org/ibis#](http://purl.org/ibis#)
PREFIX aif:    [http://www.arg.tech/aif#](http://www.arg.tech/aif#)
PREFIX prov:   [http://www.w3.org/ns/prov#](http://www.w3.org/ns/prov#)
PREFIX schema: [http://schema.org/](http://schema.org/)
PREFIX rdfs:   [http://www.w3.org/2000/01/rdf-schema#](http://www.w3.org/2000/01/rdf-schema#)

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
🎓 Academic Context & CitationDeveloped as part of the Digital Humanities Minor (Talos Project) at the University of Crete and presented at the Semantic Annotation for the Ancient World (SAW 2026) conference in Rethymno, Crete.Code snippet@article{talos2026discourse,
  title={Talos: An Agentic Discourse Extraction Engine for Democratic Deliberation via Micro-Ontology Synthesis},
  author={Department of Applied Mathematics \& Digital Humanities},
  institution={University of Crete},
  year={2026}
}
📄 LicenseDistributed under the MIT License.
