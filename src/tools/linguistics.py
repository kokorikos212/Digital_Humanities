"""
Linguistic analysis tools — POS tagging, NER, dependency parsing, and
displaCy SVG visualizations.

Uses spaCy for NLP and produces structured annotation suitable for
downstream ontology generation.
"""

from __future__ import annotations

import time
from typing import Dict, List, Literal, Type

import spacy
from pydantic import BaseModel, Field

from src.config import config


# ═══════════════════════════════════════════════════════════════════════════
# Input schemas
# ═══════════════════════════════════════════════════════════════════════════


class AnalysisInput(BaseModel):
    """Extract tokens, POS tags, dependencies, and named entities from text."""

    text: str = Field(..., description="The sentence or utterance to analyze.")


class VisualizationInput(BaseModel):
    """Create a displaCy SVG visualization of text."""

    text: str = Field(..., description="The text to visualize.")
    style: Literal["dep", "ent"] = Field(
        "dep",
        description="'dep' for dependency tree, 'ent' for entity display.",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tool implementation
# ═══════════════════════════════════════════════════════════════════════════


class LinguisticTools:
    """Linguistic analysis backed by spaCy.

    Parameters
    ----------
    model:
        spaCy model name (default: ``en_core_web_sm``).
    """

    def __init__(self, model: str | None = None):
        self.nlp = spacy.load(model or config.spacy_model)
        config.ensure_output_dirs()

    # ── Public tool methods ──────────────────────────────────────────

    def get_tags(self, text: str) -> Dict:
        """Extract full linguistic annotation from *text*.

        Returns a dictionary with ``tokens``, ``entities``, ``dependencies``,
        ``noun_chunks``, and ``root_verb`` — everything the triple generator
        and Obsidian builder need.
        """
        doc = self.nlp(text)

        # Tokens with full annotation
        tokens = []
        for t in doc:
            tokens.append(
                {
                    "index": t.i,
                    "text": t.text,
                    "lemma": t.lemma_,
                    "pos": t.pos_,
                    "tag": t.tag_,
                    "dep": t.dep_,
                    "head": t.head.i,
                    "is_stop": t.is_stop,
                    "is_alpha": t.is_alpha,
                    "is_punct": t.is_punct,
                    "morph": str(t.morph),
                    "children": [c.i for c in t.children],
                }
            )

        # Named entities
        entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "token_indices": list(range(ent.start, ent.end)),
            }
            for ent in doc.ents
        ]

        # Dependency edges
        dependencies = [
            {"source": t.head.i, "target": t.i, "relation": t.dep_}
            for t in doc
            if t.dep_ != "ROOT" and t.head is not t
        ]

        # Root verb
        root_verb = None
        for t in doc:
            if t.dep_ == "ROOT" and t.pos_ == "VERB":
                root_verb = t.lemma_
                break

        # Noun chunks
        noun_chunks = [
            {
                "text": chunk.text,
                "root_index": chunk.root.i,
                "token_indices": list(range(chunk.start, chunk.end)),
            }
            for chunk in doc.noun_chunks
        ]

        return {
            "text": text,
            "tokens": tokens,
            "entities": entities,
            "dependencies": dependencies,
            "noun_chunks": noun_chunks,
            "root_verb": root_verb,
        }

    def generate_viz(self, text: str, style: str = "dep") -> Dict[str, str]:
        """Render *text* as an SVG via spaCy displaCy.

        Returns ``{"status": "success", "saved_at": "<path>"}``.
        """
        doc = self.nlp(text)
        svg = spacy.displacy.render(doc, style=style, page=False)
        filename = f"viz_{style}_{int(time.time())}.svg"
        full_path = str(config.graphs_dir / filename)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(svg)

        return {"status": "success", "saved_at": full_path}

    # ── Metadata helper ──────────────────────────────────────────────

    @staticmethod
    def generate_tool_metadata(name: str, model: Type[BaseModel]) -> dict:
        """Produce a tool-definition dict from a Pydantic model."""
        schema = model.model_json_schema()
        schema.pop("title", None)
        if "properties" in schema:
            for prop in schema["properties"].values():
                prop.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": model.__doc__,
                "parameters": schema,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════

linguistic_registry: List = [
    ("get_tags", AnalysisInput),
    ("generate_viz", VisualizationInput),
]
