"""
Triple Generator — converts linguistic/conversation analysis into RDF triples.

Uses rdflib to produce proper RDF graphs with ontology-aligned vocabulary.
The tool accepts structured entity and relation data and returns serialized
triples plus a Turtle-serialized RDF graph saved to disk.
"""

from __future__ import annotations

import json
import re
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
        "ibis": "http://purl.org/ibis#",
        "aif": "http://www.arg.tech/aif#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "prov": "http://www.w3.org/ns/prov#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "convokit": "http://convokit.cornell.edu/ontology/",
        "nif": "http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#",
    }

    def __init__(self):
        config.ensure_output_dirs()
        self._has_rdflib = False
        self._entity_registry: Dict[str, str] = {}  # per-instance → thread-safe
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
        # Reset entity registry per run to avoid cross-pipeline contamination
        self._entity_registry.clear()

        merged_prefixes = {**self.DEFAULT_PREFIXES, **(prefixes or {})}
        triples = self._build_triples(entities, relations, merged_prefixes)
        triples = self._bind_isolated_nodes(triples)

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

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Normalize a label to a canonical form for deduplication."""
        norm = label.strip()
        # Split camelCase / PascalCase
        norm = re.sub(r"([a-z])([A-Z])", r"\1_\2", norm)
        # Lowercase and replace non-alphanumeric with underscore
        norm = norm.lower()
        norm = re.sub(r"[^a-z0-9]+", "_", norm)
        norm = norm.strip("_")
        return norm

    def _canonical_id(self, raw_id: str, label: str | None = None) -> str:
        """Return a canonical entity ID, deduplicating via the instance registry.

        If *raw_id* looks like a CURIE (contains ':'), use it as-is.
        Otherwise normalize *label* (or *raw_id*) and look up / register
        in the entity registry so that variants like 'Stanford University',
        'StanfordUniversity', and 'stanford_university' resolve to the
        same ``ex:Stanford_University`` URI.
        """
        # Prefixed CURIE — use as-is
        if ":" in raw_id and not raw_id.startswith("http"):
            return raw_id
        # Full URI — use as-is
        if raw_id.startswith("http://") or raw_id.startswith("https://"):
            return raw_id

        # Plain string — normalize and register
        norm = self._normalize_label(label or raw_id)
        if norm in self._entity_registry:
            return self._entity_registry[norm]

        # Mint a clean ex: URI
        canonical = "ex:" + "".join(
            c for c in norm.replace("_", " ").title().replace(" ", "_")
            if c.isalnum() or c == "_"
        )
        self._entity_registry[norm] = canonical
        return canonical

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
            raw_id = ent.get("id", ent.get("label", "unknown"))
            raw_label = ent.get("label", raw_id)
            entity_id = self._canonical_id(raw_id, raw_label)
            rdf_type = ent.get("rdf_type", ent.get("entity_type", "ex:Concept"))

            triples.append({
                "subject": entity_id,
                "predicate": "rdf:type",
                "object": rdf_type,
                "subject_type": "entity_id",
                "object_type": "uri" if ":" in rdf_type else "entity_id",
            })

            triples.append({
                "subject": entity_id,
                "predicate": "rdfs:label",
                "object": raw_label,
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

            subj = _get("subject")
            obj = _get("object") if _get("object") != "??" else _get("obj")

            # Normalize subject/object against entity registry
            canonical_subj = self._canonical_id(subj) if subj != "??" else subj
            canonical_obj = self._canonical_id(obj) if obj != "??" else obj

            triples.append({
                "subject": canonical_subj,
                "predicate": _get("predicate"),
                "object": canonical_obj,
                "subject_type": _get("subject_type", "entity_id"),
                "object_type": _get("object_type", "entity_id"),
                "datatype": _get("datatype", None),
            })

        return triples

    @staticmethod
    def _bind_isolated_nodes(triples: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Auto-bind any node with degree=0 to the nearest ibis:Issue or prov:Activity.

        Scans all subjects and objects.  Any entity that appears only once
        (isolated rdf:type or rdfs:label declaration) gets a ``schema:about``
        edge to the first ibis:Issue or prov:Activity found in the graph.
        """
        # Gather all nodes and their occurrences
        subjects: Dict[str, int] = {}
        objects: Dict[str, int] = {}
        issues: list = []
        activities: list = []

        for t in triples:
            s, o = t["subject"], t["object"]
            subjects[s] = subjects.get(s, 0) + 1
            objects[o] = objects.get(o, 0) + 1
            # Track root issue / activity nodes
            if t["predicate"] == "rdf:type":
                if o in ("ibis:Issue", "prov:Activity"):
                    (issues if "Issue" in o else activities).append(s)

        # Candidates for binding: any ibis:Issue or prov:Activity
        anchors = issues or activities or []

        # Find nodes appearing only as subject (an rdf:type declaration) and
        # never as object — these are likely isolated domain entities
        for t in triples:
            subj = t["subject"]
            if subj not in objects and t["predicate"] == "rdf:type" and anchors:
                # Skip already-bound entities (subj appears as object in other triples)
                obj_count = sum(1 for rt in triples if rt["object"] == subj)
                if obj_count == 0:
                    triples.append({
                        "subject": anchors[0],
                        "predicate": "schema:about",
                        "object": subj,
                        "subject_type": "uri",
                        "object_type": "uri",
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


# ── Centrality & Cognitive Distillation ────────────────────────────────────


def compute_hub_nodes(
    rdf_graph: "rdflib.Graph",  # noqa: F821
    top_n: int = 5,
) -> list:
    r"""Calculate centrality metrics for :math:`\text{skos:Concept}` nodes.

    Computes **degree centrality** :math:`C_D(v)` and **closeness
    centrality** :math:`C_C(v)` over the subset of nodes typed as
    ``skos:Concept``, then returns the *top_n* hub nodes ranked by
    degree centrality (descending).

    .. math::

        C_D(v) = \text{deg}(v)

        C_C(v) = \frac{|\mathcal{V}| - 1}
                      {\sum_{u \neq v} d(v, u)}

    For disconnected components, :math:`C_C(v) = 0.0` (the sum of
    distances is infinite but we guard with a zero fallback).

    Parameters
    ----------
    rdf_graph:
        An :class:`rdflib.Graph` containing the discourse ontology.
    top_n:
        Number of top hub nodes to return (default 5).

    Returns
    -------
    list[dict]
        Each dict has keys ``node`` (URI string), ``label`` (rdfs:label),
        ``degree_centrality`` (:math:`C_D`), ``closeness_centrality``
        (:math:`C_C`), and ``type`` (rdf:type).  Sorted by
        ``degree_centrality`` descending.

        Returns an **empty list** if the graph has :math:`|\mathcal{V}| \le 1`
        or contains no ``skos:Concept`` nodes.

    Raises
    ------
    InvalidParameterError
        If *top_n* ≤ 0.

    Examples
    --------
    >>> from rdflib import Graph, Namespace, RDF, RDFS
    >>> SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
    >>> EX = Namespace("http://example.org/")
    >>> g = Graph()
    >>> g.add((EX.A, RDF.type, SKOS.Concept))
    >>> g.add((EX.A, RDFS.label, "Budget"))
    >>> g.add((EX.B, RDF.type, SKOS.Concept))
    >>> g.add((EX.B, RDFS.label, "Housing"))
    >>> g.add((EX.A, EX.reframes, EX.B))
    >>> hubs = compute_hub_nodes(g, top_n=3)
    >>> len(hubs) == 2
    True
    >>> hubs[0]["degree_centrality"] > 0
    True
    """
    from src.analytics.health_diagnostics import InvalidParameterError

    if top_n <= 0:
        raise InvalidParameterError(
            f"top_n must be a positive integer, got {top_n}"
        )

    try:
        import rdflib
        from rdflib.namespace import RDF, RDFS
    except ImportError as exc:
        raise ImportError(
            "rdflib is required for hub-node centrality. "
            "Install it with: pip install rdflib"
        ) from exc

    import networkx as nx

    SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

    # ── Identify skos:Concept nodes ─────────────────────────────────────
    concept_nodes: set = set()
    for s in rdf_graph.subjects(RDF.type, SKOS.Concept):
        concept_nodes.add(str(s))

    if len(concept_nodes) <= 1:
        return []

    # ── Build networkx DiGraph from the RDF graph ────────────────────────
    G = nx.DiGraph()
    for s, p, o in rdf_graph:
        s_str, o_str = str(s), str(o)
        G.add_node(s_str)
        G.add_node(o_str)
        G.add_edge(s_str, o_str, predicate=str(p))

    total_nodes = G.number_of_nodes()
    if total_nodes <= 1:
        return []

    # ── Compute centrality for each skos:Concept ─────────────────────────
    degree_cent = nx.degree_centrality(G)
    try:
        closeness_cent = nx.closeness_centrality(G)
    except ZeroDivisionError:
        # All nodes isolated — closeness is undefined
        closeness_cent = {n: 0.0 for n in G.nodes()}

    results: list = []
    for node_uri in concept_nodes:
        label = _resolve_rdf_label(rdf_graph, node_uri)
        rdf_types = _resolve_rdf_types(rdf_graph, node_uri)

        results.append({
            "node": node_uri,
            "label": label,
            "degree_centrality": round(degree_cent.get(node_uri, 0.0), 6),
            "closeness_centrality": round(closeness_cent.get(node_uri, 0.0), 6),
            "type": rdf_types,
        })

    results.sort(key=lambda d: d["degree_centrality"], reverse=True)
    return results[:top_n]


def distill_cognitive_tools(
    rdf_graph: "rdflib.Graph",  # noqa: F821
) -> list:
    r"""Extract reframing edge paths — the cognitive distillation filter.

    Queries the RDF graph for paths matching:

    .. math::

        (\text{?source}) \xrightarrow{\text{ibis:reframes / ibis:resolves}}
        (\text{?target})

    These edges represent the *cognitive tool* of reframing: moments where
    a deliberative turn synthesises or resolves a friction point rather
    than rebutting it.  This implements an automated digital Grounded Theory
    coding pass over the extracted ontology.

    Parameters
    ----------
    rdf_graph:
        An :class:`rdflib.Graph` containing the discourse ontology.

    Returns
    -------
    list[dict]
        Each dict has keys ``source``, ``predicate``, ``target``,
        ``source_label``, ``target_label``, ``source_type``, ``target_type``
        describing one reframing edge.  Empty list if no reframing edges
        exist.

    Examples
    --------
    >>> from rdflib import Graph, Namespace, RDF, RDFS
    >>> IBIS = Namespace("http://purl.org/ibis#")
    >>> EX = Namespace("http://example.org/")
    >>> g = Graph()
    >>> g.add((EX.StudentObs, IBIS.reframes, EX.Issue_Budget))
    >>> g.add((EX.StudentObs, RDF.type, EX.StudentObservation))
    >>> g.add((EX.Issue_Budget, RDF.type, IBIS.Issue))
    >>> paths = distill_cognitive_tools(g)
    >>> len(paths) == 1
    True
    >>> paths[0]["predicate"] == "http://purl.org/ibis#reframes"
    True
    """
    try:
        import rdflib
        from rdflib.namespace import RDF
    except ImportError as exc:
        raise ImportError(
            "rdflib is required for cognitive-tool distillation. "
            "Install it with: pip install rdflib"
        ) from exc

    IBIS = rdflib.Namespace("http://purl.org/ibis#")

    reframing_predicates = [
        IBIS.reframes,
        IBIS.resolves,
        # Also match full URIs in case prefixes aren't bound
        rdflib.URIRef("http://purl.org/ibis#reframes"),
        rdflib.URIRef("http://purl.org/ibis#resolves"),
    ]

    # Deduplicate while preserving order
    seen: set = set()
    unique_preds = []
    for p in reframing_predicates:
        if p not in seen:
            seen.add(p)
            unique_preds.append(p)

    results: list = []
    for pred in unique_preds:
        for s, o in rdf_graph.subject_objects(pred):
            s_str, o_str = str(s), str(o)
            results.append({
                "source": s_str,
                "predicate": str(pred),
                "target": o_str,
                "source_label": _resolve_rdf_label(rdf_graph, s_str),
                "target_label": _resolve_rdf_label(rdf_graph, o_str),
                "source_type": _resolve_rdf_types(rdf_graph, s_str),
                "target_type": _resolve_rdf_types(rdf_graph, o_str),
            })

    return results


# ── RDF utility helpers ────────────────────────────────────────────────────


def _resolve_rdf_label(
    graph: "rdflib.Graph",  # noqa: F821
    uri_str: str,
) -> str:
    """Resolve the ``rdfs:label`` for a URI node, falling back to its local name."""
    try:
        import rdflib
        from rdflib.namespace import RDFS
    except ImportError:
        return uri_str.rsplit("/", 1)[-1].rsplit("#", 1)[-1] if "/" in uri_str or "#" in uri_str else uri_str

    try:
        uri = rdflib.URIRef(uri_str)
    except Exception:
        return uri_str

    for label in graph.objects(uri, RDFS.label):
        return str(label)

    # Fallback: local name
    if "#" in uri_str:
        return uri_str.rsplit("#", 1)[-1]
    if "/" in uri_str:
        return uri_str.rsplit("/", 1)[-1]
    return uri_str


def _resolve_rdf_types(
    graph: "rdflib.Graph",  # noqa: F821
    uri_str: str,
) -> list:
    """Return the list of ``rdf:type`` values for a URI node."""
    try:
        import rdflib
        from rdflib.namespace import RDF
    except ImportError:
        return []

    try:
        uri = rdflib.URIRef(uri_str)
    except Exception:
        return []

    return [str(t) for t in graph.objects(uri, RDF.type)]
