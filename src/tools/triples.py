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
        """Build a flat list of triple dicts from entities + relations.

        Propagates ``subject_type``, ``object_type``, and ``datatype`` from
        relation dicts so the serializer can produce correct RDF terms.
        """
        triples: List[Dict[str, str]] = []

        for ent in entities:
            entity_id = ent.get("id", ent.get("label", "unknown"))
            rdf_type = ent.get("rdf_type", ent.get("entity_type", "ex:Concept"))
            triples.append({
                "subject": entity_id,
                "predicate": "rdf:type",
                "object": rdf_type,
                "subject_type": "entity_id",
                "object_type": "uri" if ":" in rdf_type else "entity_id",
            })

            label = ent.get("label", entity_id)
            triples.append({
                "subject": entity_id,
                "predicate": "rdfs:label",
                "object": label,
                "subject_type": "entity_id",
                "object_type": "literal",
            })

            props = ent.get("properties", {})
            for prop, val in props.items():
                triples.append({
                    "subject": entity_id,
                    "predicate": prop,
                    "object": str(val),
                    "subject_type": "entity_id",
                    "object_type": "literal",
                })

        for rel in relations:
            # Safe extraction: Pydantic model attribute OR dict key
            def _get(key: str, default: Any = "??") -> Any:
                return (
                    getattr(rel, key, None)
                    or (rel.get(key) if isinstance(rel, dict) else None)
                    or default
                )
            triples.append({
                "subject": _get("subject"),
                "predicate": _get("predicate"),
                "object": _get("object") if _get("object") != "??" else _get("obj"),
                "subject_type": _get("subject_type", "entity_id"),
                "object_type": _get("object_type", "entity_id"),
                "datatype": _get("datatype", None),
            })

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
            s = self._to_rdflib_term(t["subject"], ns_map, position="subject")
            p = self._to_rdflib_term(t["predicate"], ns_map, position="predicate")
            o = self._to_rdflib_term(
                t["object"], ns_map,
                position="object",
                datatype=t.get("datatype"),
            )
            if s is not None and p is not None and o is not None:
                g.add((s, p, o))

        _ = RDF, RDFS, OWL
        return g.serialize(format=format) or ""

    @staticmethod
    def _to_rdflib_term(
        token: Any,
        ns_map: Dict[str, Any],
        position: str = "object",
        datatype: Optional[str] = None,
    ):
        """Convert a value to an rdflib term, position-aware and type-safe.

        - Pass-through: already an rdflib term → return as-is.
        - None / empty: return None.
        - ``subject`` / ``predicate``: always resolve to URIRef (never Literal).
        - ``object``: may be URIRef or typed Literal.
        """
        import rdflib

        # -- pass-through already-resolved rdflib terms --
        if isinstance(token, (rdflib.URIRef, rdflib.Literal, rdflib.BNode)):
            return token

        # -- None / empty guard --
        if token is None:
            return None
        if isinstance(token, str) and not token.strip():
            return None

        # -- type casting for primitives --
        if isinstance(token, (int, float, bool)):
            token = str(token)

        if not isinstance(token, str):
            token = str(token)

        # -- full URI — always a resource --
        if token.startswith("http://") or token.startswith("https://"):
            return rdflib.URIRef(token)

        # -- prefixed name like ex:Person or rdf:type --
        if ":" in token:
            prefix, _, local = token.partition(":")
            if prefix in ns_map:
                return ns_map[prefix][local]
            # Unknown prefix — URI for subj/pred, Literal for obj
            if position in ("subject", "predicate"):
                return rdflib.URIRef(token)
            return rdflib.Literal(token, datatype=datatype) if datatype else rdflib.Literal(token)

        # -- plain token: subjects/predicates become URIRefs under default ns --
        if position in ("subject", "predicate"):
            ex_ns = ns_map.get("ex")
            if ex_ns is not None:
                return ex_ns[token]
            return rdflib.URIRef(token)

        # -- object: typed or plain literal --
        return rdflib.Literal(token, datatype=datatype) if datatype else rdflib.Literal(token)

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
