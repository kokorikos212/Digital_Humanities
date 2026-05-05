# Digital Humanities: Agentic Discourse Analysis Prototype

An interdisciplinary framework integrating **Computational Linguistics** and **Agentic Workflows** to visualize discourse structures and verify integrity in political and journalistic media.

---

## 🚀 Overview
This prototype explores the transition from raw text data to structured, visual discourse maps. By leveraging Large Language Models (LLMs) as autonomous agents, the system performs **semantic intent parsing** to detect latent political concepts and nuanced narratives.

## 🛠️ Project Structure

```text
.
├── agent/                      # Core AI Agent Environment
│   ├── agent.py                # Main execution logic
│   ├── database/               # Local data & configuration
│   │   ├── config.json         # Tool and model parameters
│   │   ├── envariables.json    # API Keys (⚠️ DO NOT PUSH)
│   │   └── system_prompt.json  # Persona definitions
│   ├── output/graphs/          # Generated SVGs (Linguistic & Graph Viz)
│   ├── tools/                  # The Agent's functional toolset
│   │   ├── preprocess.py       # Data normalization
│   │   ├── text_cleaner.py     # NLP cleaning pipelines
│   │   └── toolset.py          # Integration logic
│   └── expe.ipynb              # Experimental sandbox
├── citations.md                # Academic Foundation
└── requirements.txt            # Python dependencies
