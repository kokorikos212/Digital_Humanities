"""
Triple Generator — converts linguistic/conversation analysis into RDF triples.

Uses rdflib to produce proper RDF graphs with ontology-aligned vocabulary.
The tool accepts structured entity and relation data and returns serialized
triples plus a Turtle-serialized RDF graph saved to disk.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.config import config


# ── Input schema ──────────────────────────────────────────────────────────


class TripleGeneratorInput(BaseModel):
    """Input for the RDF triple generation tool."""

    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of entity dicts, each with at least 'id', 'rdf_type', 'label'",
    )
    relations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of relation dicts: "
            "{'subject': ..., 'predicate': ..., 'object': ...}"
        ),
    )
    prefixes: Optional[Dict[str, str]] = Field(
        None,
        description="Optional custom prefix-to-namespace mappings",
    )
    format: Literal["turtle", "json-ld", "xml", "nt"] = Field(
        "turtle", description="RDF serialization format for the saved file"
    )


# ── Tool implementation ───────────────────────────────────────────────────


class TripleGenerator:
    """Generate RDF triples from extracted entities and relations.

    On instantiation, attempts to import rdflib.  If rdflib is unavailable
    the tool falls back to a pure-Python triple list (still serialisable).
    """

    DEFAULT_PREFIXES: Dict[str, str] = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "ex": "http://example.org/ontology/",
        "convokit": "http://convokit.cornell.edu/ontology/",
        "nif": "http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#",
        "prov": "http://www.w3.org/ns/prov#",
    }

    def __init__(self):
        config.ensure_output_dirs()
        self._has_rdflib = False
        try:
            import rdflib  # noqa: F401

            self._has_rdflib = True
        except ImportError:
            pass

    # ── Public tool method ────────────────────────────────────────────

    def generate_triples(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        prefixes: Optional[Dict[str, str]] = None,
        format: str = "turtle",
    ) -> Dict[str, Any]:
        """Transform entity + relation dicts into RDF triples and persist.

        Returns a dict with ``triples`` (list), ``serialized`` (RDF string),
        and ``saved_at`` (file path).
        """
        merged_prefixes = {**self.DEFAULT_PREFIXES, **(prefixes or {})}
        triples = self._build_triples(entities, relations, merged_prefixes)

        timestamp = int(time.time())
        ext = self._extension_for(format)
        filename = f"ontology_{timestamp}.{ext}"
        filepath = str(config.rdf_dir / filename)

        serialized = self._serialize(triples, merged_prefixes, format)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(serialized)

        return {
            "triples": triples,
            "serialized": serialized,
            "saved_at": filepath,
            "format": format,
            "count": len(triples),
        }

    # ── Internals ─────────────────────────────────────────────────────

    def _build_triples(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        prefixes: Dict[str, str],
    ) -> List[Dict[str, str]]:
        """Build a flat list of triple dicts from entities + relations."""
        triples: List[Dict[str, str]] = []

        for ent in entities:
            entity_id = ent.get("id", ent.get("label", "unknown"))
            rdf_type = ent.get("rdf_type", ent.get("entity_type", "ex:Concept"))
            triples.append(
                {"subject": entity_id, "predicate": "rdf:type", "object": rdf_type}
            )

            label = ent.get("label", entity_id)
            triples.append(
                {"subject": entity_id, "predicate": "rdfs:label", "object": label}
            )

            props = ent.get("properties", {})
            for prop, val in props.items():
                triples.append(
                    {"subject": entity_id, "predicate": prop, "object": str(val)}
                )

        for rel in relations:
            triples.append(
                {
                    "subject": rel.get("subject", "??"),
                    "predicate": rel.get("predicate", "??"),
                    "object": rel.get("object", rel.get("obj", "??")),
                }
            )

        return triples

    def _serialize(
        self,
        triples: List[Dict[str, str]],
        prefixes: Dict[str, str],
        format: str,
    ) -> str:
        """Serialize triples to the requested RDF format."""
        if self._has_rdflib:
            return self._serialize_rdflib(triples, prefixes, format)
        else:
            return self._serialize_fallback(triples, prefixes, format)

    def _serialize_rdflib(
        self,
        triples: List[Dict[str, str]],
        prefixes: Dict[str, str],
        format: str,
    ) -> str:
        import rdflib
        from rdflib.namespace import RDF, RDFS, OWL

        g = rdflib.Graph()

        for short, uri in prefixes.items():
            g.bind(short, rdflib.Namespace(uri))

        ns_map: Dict[str, rdflib.Namespace] = {
            short: rdflib.Namespace(uri) for short, uri in prefixes.items()
        }

        for t in triples:
            s = self._to_rdflib_term(t["subject"], ns_map)
            p = self._to_rdflib_term(t["predicate"], ns_map)
            o = self._to_rdflib_term(t["object"], ns_map)
            if s is not None and p is not None and o is not None:
                g.add((s, p, o))

        _ = RDF, RDFS, OWL
        return g.serialize(format=format) or ""

    @staticmethod
    def _to_rdflib_term(token: str, ns_map: Dict[str, Any]):
        """Convert a string token to an rdflib term (URIRef or Literal)."""
        import rdflib

        if token.startswith("http://") or token.startswith("https://"):
            return rdflib.URIRef(token)

        if ":" in token and not token.startswith("http"):
            prefix, _, local = token.partition(":")
            if prefix in ns_map:
                return ns_map[prefix][local]
            return rdflib.Literal(token)

        return rdflib.Literal(token)

    @staticmethod
    def _serialize_fallback(
        triples: List[Dict[str, str]],
        prefixes: Dict[str, str],
        format: str,
    ) -> str:
        """Pure-Python serialization when rdflib is not available."""
        if format in ("json-ld", "jsonld"):
            return json.dumps(
                {"@context": prefixes, "@graph": triples}, indent=2
            )
        lines = []
        for short, uri in prefixes.items():
            lines.append(f"@prefix {short}: <{uri}> .")
        lines.append("")
        for t in triples:
            lines.append(f"{t['subject']} {t['predicate']} {t['object']} .")
        return "\n".join(lines)

    @staticmethod
    def _extension_for(format: str) -> str:
        return {
            "turtle": "ttl",
            "json-ld": "jsonld",
            "xml": "rdf",
            "nt": "nt",
        }.get(format, "ttl")


# ── Registry helpers ──────────────────────────────────────────────────────

triple_generator_registry = [
    ("generate_triples", TripleGeneratorInput),
]
