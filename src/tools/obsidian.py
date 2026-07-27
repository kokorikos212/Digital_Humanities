"""
Obsidian Builder — generates Obsidian-compatible markdown notes with
YAML frontmatter and [[wikilinks]].

Each note carries the structured ontological data for one entity or
utterance, enabling Obsidian's graph view to render the knowledge graph.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from src.config import config


# ── Input schema ──────────────────────────────────────────────────────────


class ObsidianBuilderInput(BaseModel):
    """Input for building an Obsidian markdown note."""

    filename: str = Field(
        ..., description="Base filename (e.g. 'utterance_001.md')"
    )
    note_type: str = Field(
        "ConversationAnalysis",
        description="Type tag placed in the YAML frontmatter",
    )
    prefixes: Dict[str, str] = Field(
        default_factory=dict,
        description="Namespace prefixes for the ontology",
    )
    entity_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value data to embed in the YAML frontmatter",
    )
    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ontological entities to link via [[wikilinks]]",
    )
    body_sections: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Sections to render in the markdown body: [{heading, content}]",
    )
    tags: List[str] = Field(
        default_factory=list, description="Obsidian tags (without # prefix)"
    )


# ── Tool implementation ───────────────────────────────────────────────────


class ObsidianBuilder:
    """Create Obsidian-compatible markdown notes from ontological data."""

    def __init__(self):
        config.ensure_output_dirs()

    # ── Public tool method ────────────────────────────────────────────

    def build_obsidian_note(
        self,
        filename: str,
        note_type: str = "ConversationAnalysis",
        prefixes: Optional[Dict[str, str]] = None,
        entity_data: Optional[Dict[str, Any]] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        body_sections: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate an Obsidian .md note and save it to the vault.

        Returns a dict with ``filename``, ``saved_at``, ``wikilinks``,
        and a preview of the generated frontmatter.
        """
        prefixes = prefixes or {}
        entity_data = entity_data or {}
        entities = entities or []
        body_sections = body_sections or []
        tags = tags or []

        safe_name = self._safe_filename(filename)

        frontmatter: Dict[str, Any] = {
            "type": note_type,
            "rdf_type": entity_data.get("rdf_type", "ex:Concept"),
            "source_prompt": entity_data.get("source_prompt", ""),
            "prefixes": prefixes,
        }
        if "conversation_metadata" in entity_data:
            frontmatter["conversation_metadata"] = entity_data["conversation_metadata"]
        if "properties" in entity_data:
            frontmatter["properties"] = entity_data["properties"]
        if "tags" in entity_data:
            frontmatter["tags"] = entity_data["tags"]
        if tags:
            frontmatter["tags"] = tags
        if entities:
            frontmatter["entities"] = entities

        body = self._build_body(
            entity_data=entity_data,
            entities=entities,
            body_sections=body_sections,
        )

        wikilinks = self._extract_wikilinks(body)

        full_md = self._render_note(frontmatter, body)
        filepath = str(config.verse_dir / safe_name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_md)

        return {
            "filename": safe_name,
            "saved_at": filepath,
            "wikilinks": wikilinks,
            "frontmatter_preview": frontmatter,
            "character_count": len(full_md),
        }

    # ── Body rendering ────────────────────────────────────────────────

    def _build_body(
        self,
        entity_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        body_sections: List[Dict[str, str]],
    ) -> str:
        """Compose the markdown body from entity data and sections."""
        parts: List[str] = []

        if entity_data.get("source_prompt"):
            parts.append(f"> **Source:** {entity_data['source_prompt']}\n")

        if entities:
            parts.append("## Linked Entities\n")
            for ent in entities:
                eid = ent.get("id", ent.get("label", "?"))
                etype = ent.get("rdf_type", ent.get("entity_type", ""))
                label = ent.get("label", eid)
                parts.append(f"- **[[{eid}]]** ({etype}): {label}")
                props = ent.get("properties", {})
                if props:
                    for k, v in props.items():
                        short_k = k.split(":")[-1] if ":" in k else k
                        parts.append(f"  - {short_k}: `{v}`")
            parts.append("")

        for sec in body_sections:
            heading = sec.get("heading", "")
            content = sec.get("content", "")
            if heading:
                parts.append(f"## {heading}\n")
            if content:
                parts.append(content)
            parts.append("")

        return "\n".join(parts)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _render_note(frontmatter: Dict[str, Any], body: str) -> str:
        """Produce the final markdown string with YAML frontmatter."""
        yaml_block = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        ).strip()
        return f"---\n{yaml_block}\n---\n\n{body}"

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Ensure the filename is safe and ends with .md."""
        name = name.strip()
        name = re.sub(r"[^\w\-.,()\[\] ]", "_", name)
        name = re.sub(r"\s+", "_", name)
        if not name.lower().endswith(".md"):
            name += ".md"
        return name

    @staticmethod
    def _extract_wikilinks(body: str) -> List[str]:
        """Extract [[wikilink]] targets from the markdown body."""
        return re.findall(r"\[\[([^\]]+)\]\]", body)


# ── Registry helpers ──────────────────────────────────────────────────────

obsidian_builder_registry = [
    ("build_obsidian_note", ObsidianBuilderInput),
]
