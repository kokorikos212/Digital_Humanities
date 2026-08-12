r"""
Micro-Ontology Mapping Layer — IBIS & AIF Schema Alignment.

Deterministic parser functions that convert raw Markdown frontmatter,
Obsidian tags, and claim annotations into formal RDF namespaces.

.. math::

    \text{\#friction} \xrightarrow{\text{map}} \text{ibis:Issue}

    \text{claim} \xrightarrow{\text{map}} \text{aif:I-node}
    \xrightarrow{\text{edge}} \{\text{aif:conflicts},\; \text{aif:supports}\}

These functions provide the **deterministic backbone** that complements the
LLM-driven prompt engineering in :mod:`src.prompts`.  They can be used for
post-hoc verification that the agent's output conforms to IBIS/AIF semantics.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.analytics.health_diagnostics import InvalidParameterError


# ── Namespace Constants ─────────────────────────────────────────────────────

IBIS_NS = "http://purl.org/ibis#"
AIF_NS = "http://www.arg.tech/aif#"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
SCHEMA_NS = "http://schema.org/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
EX_NS = "http://example.org/ontology/"

IBIS = {
    "Issue": f"{IBIS_NS}Issue",
    "Position": f"{IBIS_NS}Position",
    "rebuts": f"{IBIS_NS}rebuts",
    "reframes": f"{IBIS_NS}reframes",
    "respondsTo": f"{IBIS_NS}respondsTo",
    "endorses": f"{IBIS_NS}endorses",
    "asserts": f"{IBIS_NS}asserts",
    "resolves": f"{IBIS_NS}resolves",
}

AIF = {
    "I-node": f"{AIF_NS}I-node",
    "conflicts": f"{AIF_NS}conflicts",
    "supports": f"{AIF_NS}supports",
    "claimText": f"{AIF_NS}claimText",
}


# ── Tag → Issue Mapping ────────────────────────────────────────────────────


def map_friction_tag_to_ibis_issue(
    tag: str,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    r"""Convert a ``#friction`` Obsidian tag into an :math:`\text{ibis:Issue}` triple dict.

    Parameters
    ----------
    tag:
        Raw tag string, e.g. ``"#friction/budget_allocation"`` or
        ``"friction"``.  Leading ``#`` is stripped automatically.
    label:
        Human-readable label for the issue.  Defaults to a title-cased
        version of the tag slug.

    Returns
    -------
    dict
        A triple-like dict with keys ``subject``, ``predicate``, ``object``,
        ``subject_type``, ``object_type`` representing the
        ``rdf:type ibis:Issue`` declaration.

    Raises
    ------
    InvalidParameterError
        If *tag* is empty or does not contain the substring ``"friction"``.

    Examples
    --------
    >>> result = map_friction_tag_to_ibis_issue("#friction/budget_allocation")
    >>> result["predicate"]
    'rdf:type'
    >>> result["object"]
    'ibis:Issue'
    >>> "Budget_Allocation" in result["subject"]
    True
    """
    clean = (tag or "").strip().lstrip("#")

    if not clean:
        raise InvalidParameterError(
            f"Tag must be a non-empty string, got {tag!r}"
        )

    if "friction" not in clean.lower():
        raise InvalidParameterError(
            f"Tag {tag!r} does not contain 'friction'. "
            "Only friction-tagged cards map to ibis:Issue."
        )

    # Derive a canonical CURIE from the tag path
    slug = clean.replace("friction", "").strip("/").replace("/", "_").replace(" ", "_")
    if not slug:
        slug = "unnamed_friction"

    # PascalCase the slug for a clean ex: CURIE
    canonical = "ex:" + "".join(
        c for c in slug.replace("_", " ").title().replace(" ", "_")
        if c.isalnum() or c == "_"
    )

    if label is None:
        label = slug.replace("_", " ").title()

    return {
        "subject": canonical,
        "predicate": "rdf:type",
        "object": "ibis:Issue",
        "subject_type": "uri",
        "object_type": "uri",
    }


# ── Claim → AIF I-node Mapping ──────────────────────────────────────────────


def map_claim_to_aif_inode(
    claim_label: str,
    claim_text: str = "",
    speaker_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    r"""Convert a deliberative claim into :math:`\text{aif:I-node}` RDF triples.

    Produces the triple cluster:

    .. math::

        \text{ex:Claim\_X} &\xrightarrow{\text{rdf:type}} \text{ibis:Position} \\
        &\xrightarrow{\text{rdf:type}} \text{aif:I-node} \\
        &\xrightarrow{\text{rdfs:label}} \text{<claim\_label>} \\
        &\xrightarrow{\text{aif:claimText}} \text{<claim\_text>}

    Optionally links the speaker via :math:`\text{ibis:asserts}`.

    Parameters
    ----------
    claim_label:
        Short 3–7 word summary label (becomes ``rdfs:label``).
    claim_text:
        Full verbatim claim text (becomes ``aif:claimText`` literal).
    speaker_id:
        Optional speaker CURIE (e.g. ``"ex:Dr_Chen"``).  When provided, an
        additional ``ibis:asserts`` edge is emitted.

    Returns
    -------
    list[dict]
        A list of triple dicts.  Always includes ``rdf:type`` (×2),
        ``rdfs:label``, and ``aif:claimText``.  Includes ``ibis:asserts``
        when *speaker_id* is provided.

    Raises
    ------
    InvalidParameterError
        If *claim_label* is empty.

    Examples
    --------
    >>> triples = map_claim_to_aif_inode(
    ...     "ML models detect bias",
    ...     "Machine learning models can detect bias in political speeches.",
    ...     speaker_id="ex:Dr_Chen",
    ... )
    >>> len(triples) >= 5
    True
    >>> any(t["predicate"] == "aif:claimText" for t in triples)
    True
    """
    if not claim_label or not claim_label.strip():
        raise InvalidParameterError("claim_label must be a non-empty string.")

    label = claim_label.strip()
    text = (claim_text or "").strip()

    # Mint canonical CURIE from label
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    canonical = "ex:Claim_" + "".join(
        c for c in slug.replace("_", " ").title().replace(" ", "_")
        if c.isalnum() or c == "_"
    )

    triples: List[Dict[str, Any]] = [
        {
            "subject": canonical,
            "predicate": "rdf:type",
            "object": "ibis:Position",
            "subject_type": "uri",
            "object_type": "uri",
        },
        {
            "subject": canonical,
            "predicate": "rdf:type",
            "object": "aif:I-node",
            "subject_type": "uri",
            "object_type": "uri",
        },
        {
            "subject": canonical,
            "predicate": "rdfs:label",
            "object": label,
            "subject_type": "uri",
            "object_type": "literal",
        },
    ]

    if text:
        triples.append({
            "subject": canonical,
            "predicate": "aif:claimText",
            "object": text,
            "subject_type": "uri",
            "object_type": "literal",
            "datatype": "xsd:string",
        })

    if speaker_id:
        triples.append({
            "subject": speaker_id.strip(),
            "predicate": "ibis:asserts",
            "object": canonical,
            "subject_type": "uri",
            "object_type": "uri",
        })

    return triples


# ── Edge Semantics Classifier ───────────────────────────────────────────────


def classify_edge_semantics(
    relation_type: str,
) -> Dict[str, Any]:
    r"""Map a deliberative speech-act label to its IBIS + AIF edge pair.

    .. math::

        \text{Pure rebuttal} &\rightarrow \{\text{ibis:rebuts},\; \text{aif:conflicts}\} \\
        \text{Partial agreement} &\rightarrow \{\text{aif:supports},\; \text{ibis:endorses}\} \\
        \text{Synthesis} &\rightarrow \{\text{ibis:respondsTo},\; \text{ibis:reframes}\}

    Parameters
    ----------
    relation_type:
        One of ``"rebuttal"``, ``"agreement"``, ``"synthesis"``
        (case-insensitive).

    Returns
    -------
    dict
        Keys ``ibis_edge`` (the primary IBIS predicate CURIE) and
        ``aif_edge`` (the primary AIF predicate CURIE), plus a
        ``classification`` label.

    Raises
    ------
    InvalidParameterError
        If *relation_type* is not one of the three recognised speech-act
        categories.

    Examples
    --------
    >>> classify_edge_semantics("rebuttal")
    {'ibis_edge': 'ibis:rebuts', 'aif_edge': 'aif:conflicts', 'classification': 'pure_rebuttal'}
    >>> classify_edge_semantics("Synthesis")["ibis_edge"]
    'ibis:respondsTo'
    """
    mapping: Dict[str, Tuple[str, str, str]] = {
        "rebuttal": ("ibis:rebuts", "aif:conflicts", "pure_rebuttal"),
        "agreement": ("ibis:endorses", "aif:supports", "partial_agreement"),
        "synthesis": ("ibis:respondsTo", "aif:reframes_or_supports", "synthesis_alternative"),
    }

    key = (relation_type or "").strip().lower()
    if key not in mapping:
        raise InvalidParameterError(
            f"Unknown relation_type {relation_type!r}. "
            f"Expected one of: {', '.join(sorted(mapping.keys()))}"
        )

    ibis_edge, aif_edge, classification = mapping[key]
    return {
        "ibis_edge": ibis_edge,
        "aif_edge": aif_edge,
        "classification": classification,
    }


# ── Frontmatter Validation & Parsing ────────────────────────────────────────


def validate_frontmatter(frontmatter: Dict[str, Any]) -> None:
    r"""Validate an Obsidian YAML frontmatter dict before RDF instantiation.

    Checks for required keys and well-formed tag strings.  Raises
    :exc:`InvalidParameterError` on the first violation so callers can
    reject malformed input before any triples are generated.

    Parameters
    ----------
    frontmatter:
        A dict parsed from YAML frontmatter.  Must contain at least one
        recognised key from ``{"tags", "rdf_type", "id", "label"}``.

    Raises
    ------
    InvalidParameterError
        If *frontmatter* is empty, ``tags`` contains non-string entries,
        or ``rdf_type`` is missing a CURIE prefix.

    Examples
    --------
    >>> validate_frontmatter({"tags": ["friction/budget"], "id": "note_1"})
    >>> validate_frontmatter({"tags": [123]})
    Traceback (most recent call last):
        ...
    src.analytics.health_diagnostics.InvalidParameterError: ...
    """
    if not frontmatter:
        raise InvalidParameterError("Frontmatter dict is empty — nothing to validate.")

    recognised = {"tags", "rdf_type", "id", "label", "aliases", "cssclass"}
    if not any(k in frontmatter for k in recognised):
        raise InvalidParameterError(
            f"Frontmatter contains no recognised keys. "
            f"Expected at least one of: {', '.join(sorted(recognised))}"
        )

    # Validate tags
    tags = frontmatter.get("tags", [])
    if tags is None:
        tags = []
    if isinstance(tags, str):
        tags = [tags]

    for i, t in enumerate(tags):
        if not isinstance(t, str):
            raise InvalidParameterError(
                f"Frontmatter tag at index {i} must be a string, got {type(t).__name__}: {t!r}"
            )

    # Validate rdf_type has CURIE prefix if present
    rdf_type = frontmatter.get("rdf_type", "")
    if rdf_type and ":" not in str(rdf_type):
        raise InvalidParameterError(
            f"Frontmatter rdf_type {rdf_type!r} is missing a CURIE prefix "
            f"(expected e.g. 'ibis:Issue', 'aif:I-node')."
        )


def parse_frontmatter_to_triples(
    frontmatter: Dict[str, Any],
    note_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    r"""Convert a validated Obsidian YAML frontmatter dict into RDF triples.

    Mapping rules:

    - ``tags`` containing ``"friction"`` → ``ibis:Issue`` type declaration.
    - ``rdf_type`` → ``rdf:type`` triple (must be a CURIE).
    - ``id`` → ``rdfs:label`` triple.
    - ``label`` → ``rdfs:label`` triple (if different from ``id``).
    - ``aliases`` → additional ``rdfs:label`` triples.

    Parameters
    ----------
    frontmatter:
        A validated YAML frontmatter dict.  Call :func:`validate_frontmatter`
        first to ensure correctness.
    note_id:
        Explicit note identifier.  When omitted, falls back to
        ``frontmatter["id"]``, then to ``"ex:Note"``.

    Returns
    -------
    list[dict]
        A list of triple dicts ready for ingestion by
        :class:`~src.tools.triples.TripleGenerator`.

    Raises
    ------
    InvalidParameterError
        If validation fails (delegates to :func:`validate_frontmatter`).

    Examples
    --------
    >>> triples = parse_frontmatter_to_triples(
    ...     {"tags": ["friction/budget"], "id": "note_001", "label": "Budget Debate"},
    ... )
    >>> any(t["object"] == "ibis:Issue" for t in triples)
    True
    """
    validate_frontmatter(frontmatter)

    resolved_id = note_id or frontmatter.get("id", "ex:Note")
    # Ensure CURIE form
    if ":" not in str(resolved_id) and not str(resolved_id).startswith("http"):
        resolved_id = f"ex:{resolved_id}"

    triples: List[Dict[str, Any]] = []

    # ── rdf:type ────────────────────────────────────────────────────────
    rdf_type = frontmatter.get("rdf_type", "")
    if rdf_type:
        triples.append({
            "subject": resolved_id,
            "predicate": "rdf:type",
            "object": str(rdf_type),
            "subject_type": "uri",
            "object_type": "uri",
        })

    # ── Tags → ibis:Issue ───────────────────────────────────────────────
    tags = frontmatter.get("tags", [])
    if tags is None:
        tags = []
    if isinstance(tags, str):
        tags = [tags]

    has_friction = any("friction" in str(t).lower() for t in tags)
    if has_friction and not rdf_type:
        triples.append({
            "subject": resolved_id,
            "predicate": "rdf:type",
            "object": "ibis:Issue",
            "subject_type": "uri",
            "object_type": "uri",
        })

    # ── rdfs:label (from id and/or label) ───────────────────────────────
    label = frontmatter.get("label", "")
    note_id_val = frontmatter.get("id", "")
    if note_id_val:
        triples.append({
            "subject": resolved_id,
            "predicate": "rdfs:label",
            "object": str(note_id_val),
            "subject_type": "uri",
            "object_type": "literal",
        })
    if label and label != note_id_val:
        triples.append({
            "subject": resolved_id,
            "predicate": "rdfs:label",
            "object": str(label),
            "subject_type": "uri",
            "object_type": "literal",
        })

    # ── aliases → rdfs:label ────────────────────────────────────────────
    aliases = frontmatter.get("aliases", [])
    if aliases is None:
        aliases = []
    if isinstance(aliases, str):
        aliases = [aliases]
    for alias in aliases:
        triples.append({
            "subject": resolved_id,
            "predicate": "rdfs:label",
            "object": str(alias),
            "subject_type": "uri",
            "object_type": "literal",
        })

    return triples
