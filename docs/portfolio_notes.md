---
title: "Agentic Linguistic Analysis"
domain: ["NLP", "Computational Social Science", "Applied Mathematics"]
methods: ["RDF Triples", "Dependency Parsing", "Agentic Orchestration"]
trait: "AI Skills"
live_demo: "[https://nospadiss-agentic-linguistic-analysis.hf.space](https://nospadiss-agentic-linguistic-analysis.hf.space)"
github_repo: "[https://github.com/kokorikos212/Digital_Humanities](https://github.com/kokorikos212/Digital_Humanities)"
---

# Agentic Ontological Discourse Analysis

An interdisciplinary framework integrating **Computational Linguistics**, **Knowledge Representation (RDF/OWL)**, and **Agentic LLM Workflows** to extract structured ontologies from conversational text.

## Pipeline

1. **Linguistic Parsing** — spaCy POS tagging, NER, dependency parsing, noun chunks
2. **Conversation Analysis** — Speaker turns, reply graphs, pragmatics (politeness, toxicity)
3. **RDF Triple Generation** — Entity + relation extraction → Turtle/JSON-LD via rdflib
4. **Obsidian Vault** — Markdown notes with YAML frontmatter and `[[wikilinks]]`
5. **Semantic Graphs** — Interactive pyvis HTML network visualizations

## Tools

| Tool | Library | Output |
|------|---------|--------|
| `get_tags` | spaCy | Tokens, POS, NER, dependencies, noun chunks |
| `analyze_conversation` | Convokit | Speaker structure, reply graph, pragmatics |
| `generate_triples` | rdflib | RDF triples (Turtle / JSON-LD) |
| `build_obsidian_note` | PyYAML | `.md` with YAML frontmatter + wikilinks |
| `generate_semantic_graph` | networkx + pyvis | Interactive HTML semantic network |

## Corpora

- **Conversations Gone Awry** — 4,188 conversations, 30,021 utterances (Wikipedia talk pages)
- **Winning Arguments** — Argumentation corpus with annotated persuasion strategies

## Conference

Presented at **SAW 2026** (Semantic Annotation for the Ancient World), Rethymno, Crete.

## Links

- [[Live Demo]]
- [[GitHub Repository]]
