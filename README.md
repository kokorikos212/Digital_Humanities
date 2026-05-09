# Digital Humanities: Agentic Discourse Analysis Prototype

An interdisciplinary framework integrating **Computational Linguistics** and **Agentic Workflows** to visualize discourse structures and verify integrity in political and journalistic media.

---

## 🚀 Overview
This prototype explores the transition from raw text data to structured, visual discourse maps. By leveraging Large Language Models (LLMs) as autonomous agents, the system performs **semantic intent parsing** to detect latent political concepts and nuanced narratives.

## 🏛️ Conference & Presentation
This project was presented at the **"Semantic Annotation for the Ancient World"** conference in Rethymno (2026). The work focuses on applying modern Agentic Workflows to classical and contemporary discourse analysis.
Here is the link to the conference site: (https://talos-ai4ssh.uoc.gr/events/conferences/semantic-annotation-for-the-ancient-world-conference-2026/)

*   **Conference:** Semantic Annotation for the Ancient World
*   **Location:** Rethymno, Crete
*   **Affiliation:** Digital Humanities Minor, Talos
*   **Presentation Topic:** Argument Modeling with Agentic Workflows

📄 **[View the Research Poster (PDF)](resources/poster.pdf)** 

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
├── poster.pdf                  # Conference Presentation Poster
├── citations.md                # Academic Foundation
└── requirements.txt            # Python dependencies
