# Audit Report: Habermasian Deliberative Metrics & Micro-Ontology Schema Alignment

**Auditor**: Codebase Editor  
**Date**: 2026-08-12  
**Directive**: Senior Programmer-Mathematician — Targeted Code Review & Verification  
**Scope**: `src/tools/triples.py`, `src/tools/graph.py`, `src/schemas.py`, `src/prompts.py`, `src/queries.py`, `src/visualizer.py`

---

## Executive Summary

**The three computational modules described in the directive do not exist in the codebase.** The functions `compute_hub_nodes`, the cognitive distillation filter, IBIS/AIF mapping parsers, discursive path queries, and the connectivity ratio are **absent**. The architecture is LLM-driven (prompt engineering) rather than algorithmically computed. Below is a detailed gap analysis per target area, followed by the code that *does* exist and can serve as the foundation for building the missing modules.

---

## 1. Symbolic Capital Mapping & Grounded Theory Extraction

### 1.1 `compute_hub_nodes` — Centrality Metrics

**Status: DOES NOT EXIST**

There is no function anywhere in the codebase that computes degree centrality, closeness centrality, betweenness centrality, or any other graph-theoretic centrality measure over RDF graph entities.

**What exists instead:**

- `src/tools/graph.py` builds a `networkx.DiGraph` internally (line 110 of `graph.py`) but only to pass it to `pyvis.Network.from_nx()` — the `nx.DiGraph` object `G` is discarded after visualization.
- `src/visualizer.py` identifies **root nodes** (subjects that never appear as objects) and **terminal nodes** (objects that never appear as subjects) at lines 137–138, but only for color-coding, not centrality scoring.
- `src/schemas.py` line 468 defines `resolves_hub_nodes: List[str]` on `OntologicalRelations` — a **data field** for the LLM to populate with `[[Hub_XXX]]` wikilinks. This is a *schema slot*, not a computation.

**Gap**: The paper's formula $C_D(v) = \text{deg}(v)$ and $C_C(v) = \frac{|\mathcal{V}| - 1}{\sum_{u \neq v} d(v, u)}$ have no implementation. The extraction of $V_{\text{hub}}$ (high-centrality `skos:Concept` nodes) is entirely delegated to the LLM's structured output.

**Edge cases that would need handling (not currently handled):**
- Division by zero in closeness centrality for disconnected components ($\sum d(v,u) = \infty$)
- Multi-graph edge semantics: `ibis:rebuts` vs `aif:conflicts` are parallel edges between the same node pair — should they be collapsed or counted separately for degree?
- Isolated `skos:Concept` nodes with `rdfs:label` but no edges (currently caught by `_bind_isolated_nodes`, but that auto-binds rather than flagging them)

### 1.2 Cognitive Distillation Filter — Reframing Edge Paths

**Status: DOES NOT EXIST**

There is no function that programmatically extracts paths matching:

$$(\text{StudentObservation}) \xrightarrow{\text{ibis:reframes / resolves}} (\text{ibis:Issue / DeliberativeFriction})$$

**What exists instead:**

The prompt engineering in `src/prompts.py` lines 69–82 instructs the LLM to classify speech acts:
- Rule III(a): Pure rebuttal → `ibis:rebuts` + `aif:conflicts`
- Rule III(b): Partial agreement → `aif:supports` + `ibis:endorses`
- Rule III(c): Synthesis/alternative → `ibis:respondsTo` + `ibis:reframes`

The **SPARQL query** at `src/queries.py` lines 21–46 ("Conflict Density Indexing") queries rebuttal edges:
```sparql
?position ibis:rebuts ?targetPosition .
```
But there is no equivalent query for `ibis:reframes` paths — this is a gap even at the query level.

**Gap**: The "automated digital implementation of Grounded Theory coding" claimed in the paper is performed by the LLM via prompt rules, not by deterministic code. There is no post-hoc verification that the LLM actually followed the classification rules.

### 1.3 Existing Foundation Code (for hand-off)

**Entity deduplication registry** (`src/tools/triples.py:122–164`):

```python
_entity_registry: Dict[str, str] = {}  # normalized label → canonical URI

@staticmethod
def _normalize_label(label: str) -> str:
    norm = label.strip()
    norm = re.sub(r"([a-z])([A-Z])", r"\1_\2", norm)  # camelCase → snake_case
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "_", norm)
    norm = norm.strip("_")
    return norm

@classmethod
def _canonical_id(cls, raw_id: str, label: str | None = None) -> str:
    if ":" in raw_id and not raw_id.startswith("http"):
        return raw_id
    if raw_id.startswith("http://") or raw_id.startswith("https://"):
        return raw_id
    norm = cls._normalize_label(label or raw_id)
    if norm in cls._entity_registry:
        return cls._entity_registry[norm]
    canonical = "ex:" + "".join(
        c for c in norm.replace("_", " ").title().replace(" ", "_")
        if c.isalnum() or c == "_"
    )
    cls._entity_registry[norm] = canonical
    return canonical
```

**Isolated-node binding** (`src/tools/triples.py:238–280`):

```python
@staticmethod
def _bind_isolated_nodes(triples: List[Dict[str, str]]) -> List[Dict[str, str]]:
    subjects: Dict[str, int] = {}
    objects: Dict[str, int] = {}
    issues: list = []
    activities: list = []

    for t in triples:
        s, o = t["subject"], t["object"]
        subjects[s] = subjects.get(s, 0) + 1
        objects[o] = objects.get(o, 0) + 1
        if t["predicate"] == "rdf:type":
            if o in ("ibis:Issue", "prov:Activity"):
                (issues if "Issue" in o else activities).append(s)

    anchors = issues or activities or []

    for t in triples:
        subj = t["subject"]
        if subj not in objects and t["predicate"] == "rdf:type" and anchors:
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
```

**Bug note**: The `_entity_registry` is a **class-level** dict (`cls._entity_registry`), but `generate_triples()` clears it via `self._entity_registry.clear()` at line 96. This works because Python's MRO resolves `self._entity_registry` to the class attribute when no instance attribute shadows it, but calling `.clear()` on it from an instance mutates the **shared class state**. If two `TripleGenerator` instances run concurrently (e.g., in threaded Gradio), they will race on the same registry.

---

## 2. Micro-Ontology Mapping Layer (Section 2.2.1)

### 2.1 IBIS & AIF Mapping Functions

**Status: `src/tools/semantics.py` DOES NOT EXIST**

There is no parser function that converts raw Markdown frontmatter and tags into formal RDF namespaces. There is no deterministic mapping from `#friction` card tags to `ibis:Issue` instances. There is no programmatic conversion of claim links into `aif:I-node` entities.

**What exists instead:**

The **entire ontology mapping is prompt-driven**. The LLM receives 83 lines of SYSTEM_PROMPT rules (`src/prompts.py:17–83`) instructing it how to produce structured output conforming to the Pydantic schemas in `src/schemas.py`.

Key prompt rules:
- **Rule 11**: "Model CLAIMS made in indirect speech as `ibis:Position` or `aif:I-node` with the full proposition text as `rdfs:label`."
- **Rule 12**: "Link the speaker to the claim via `ibis:asserts` or `prov:wasAttributedTo`."
- **Rule III(a-c)**: Directional edge semantics (`ibis:rebuts` + `aif:conflicts`, `aif:supports` + `ibis:endorses`, `ibis:respondsTo` + `ibis:reframes`).

The `OntologyGraph` schema (`src/schemas.py:321–344`) is the structural contract the LLM must fill:

```python
class OntologyGraph(BaseModel):
    prefixes: Dict[str, str] = Field(default_factory=lambda: {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        # ... IBIS, AIF, SKOS are NOT in the schema's default prefixes
        # They ARE in TripleGenerator.DEFAULT_PREFIXES (triples.py:57-69)
    })
    entities: List[OntologicalEntity]
    triples: List[Triple]
```

**Critical gap**: The `OntologyGraph.prefixes` default does NOT include `ibis`, `aif`, `skos`, `prov`, or `schema` namespaces. These are only defined in `TripleGenerator.DEFAULT_PREFIXES` (`src/tools/triples.py:57–69`). If the LLM returns an `OntologyGraph` directly (bypassing `TripleGenerator`), the IBIS/AIF prefixes are absent.

### 2.2 Mental-Tool Schema (MT_k)

The `MentalTool` schema (`src/schemas.py:473–491`) with its `OntologicalRelations` sub-model is the structured container for symbolic-capital mapping:

```python
class OntologicalRelations(BaseModel):
    prerequisite_concepts: List[str]   # [[MT-XXX]] links
    synergizes_with: List[str]         # [[MT-XXX]] links
    conflicts_with: List[str]          # [[MT-XXX]] links
    resolves_hub_nodes: List[str]      # [[Hub_XXX]] links  ← THE ONLY hub reference

class MentalTool(BaseModel):
    id: str                            # e.g. 'MT-000'
    label: str
    definition: str                    # 1-2 sentence core cognitive transformation
    provenance: Optional[ProvenanceMetadata]
    contextual_validity: ContextualValidity
    mechanics: OperationalMechanics
    demonstrations: Optional[MultimodalDemonstrations]
    relations: OntologicalRelations
```

**Gap**: `resolves_hub_nodes` is a **free-text list field**. The LLM populates it with `[[Hub_XXX]]` wikilinks, but there is no validation that these hub references actually exist in the graph. No function verifies that claimed hub nodes have high centrality or are `skos:Concept` instances.

### 2.3 SPARQL Query Layer (partial coverage)

`src/queries.py` provides case-specific SPARQL queries that *query* IBIS/AIF patterns. These are user-facing presets, not automated mapping functions:

| Query | What it covers |
|-------|---------------|
| Conflict Density Indexing (lines 21–46) | `ibis:Issue` → `ibis:Position` → `ibis:rebuts` chains |
| Policy Need vs. Priority Audit (lines 47–62) | `schema:about` auto-bound entities |
| Reified Claims & Speaker Attribution (lines 65–85) | `ibis:asserts` + `aif:claimText` |
| Protasis/Apodosis Decomposition (lines 86–106) | `aif:I-node` → `schema:about` sub-triples |

**Gap**: No SPARQL query exists for `ibis:reframes` paths, `ibis:endorses` edges, or `aif:supports`/`aif:conflicts` enumeration. The query layer covers rebuttal and claim attribution but not the full IBIS/AIF edge taxonomy.

### 2.4 Existing Foundation Code (for hand-off)

**TripleGenerator.DEFAULT_PREFIXES** (`src/tools/triples.py:57–69`) — the only place IBIS/AIF/SKOS namespaces are defined in code:

```python
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
```

**OntologyGraph schema** (`src/schemas.py:321–344`) — the structural contract; note the prefix gap vs TripleGenerator.

---

## 3. Microdemocratic Health Evaluation & Discursive Path Analysis (Section 2.2.2)

### 3.1 Graph Connectivity & Topology Inspection

**Status: `src/analytics/health_diagnostics.py` DOES NOT EXIST**

There is no module that performs structural integrity checks over the global directed multi-graph $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{L})$.

**What exists instead:**

- `_bind_isolated_nodes()` in `triples.py` (lines 238–280) is a **preventative invariant**, not a diagnostic. It forces degree-0 nodes to be connected rather than measuring how many were isolated.
- `src/visualizer.py` lines 137–143 compute root/terminal nodes for color-coding but don't export these as metrics.
- The tests in `tests/test_generalized_extraction.py` validate invariants I–V (no floating entities, noise filtering, label abstraction) but these are boolean pass/fail checks, not quantitative health scores.

### 3.2 Discursive Path Queries — Connectivity Ratio

**Status: DOES NOT EXIST**

The formula:

$$\text{Ratio} = \frac{|\mathcal{V}_{\text{connected, mutually reframing}}|}{|\mathcal{V}_{\text{isolated (degree-0)}}|}$$

has no implementation. There is no:
- Query to count mutually-reframing connected nodes
- Query to count isolated (degree-0) nodes
- Function computing the ratio
- Threshold for flagging "conversational noise," "ideological siloing," or "public sphere fragmentation"

**What exists instead:**

The **closest proxy** is the SPARQL "Conflict Density Indexing" query (`src/queries.py:21–46`), which extracts rebuttal chains. A skilled user could manually compute a conflict density metric from the result set, but there is no automated function.

### 3.3 Edge Cases Not Handled

| Edge case | Where it matters | Current behavior |
|-----------|-----------------|------------------|
| Division by zero: 0 isolated nodes → infinite ratio | Connectivity ratio | Not implemented |
| Graph with only 1 node | Centrality, connectivity | Not implemented |
| Disconnected components > 1 | Closeness centrality | Not implemented |
| Self-loops (entity reframes itself) | Degree centrality | Not filtered in graph construction |
| Multi-edges between same node pair | Degree counting | networkx DiGraph handles natively but pyvis may collapse visually |
| Empty graph (no entities extracted) | All metrics | No guard; would crash or return NaN |

### 3.4 Existing Foundation Code (for hand-off)

**networkx DiGraph construction** (`src/tools/graph.py:99–133`) — the only graph construction pipeline, currently used only for visualization:

```python
def _build_graph(self, entities, relations, title, layout):
    import networkx as nx
    from pyvis.network import Network

    G = nx.DiGraph()

    for ent in entities:
        node_id = ent.get("id", ent.get("label", str(hash(str(ent)))))
        label = ent.get("label", node_id)
        etype = ent.get("rdf_type", ent.get("entity_type", "ex:Concept"))
        color = self.TYPE_COLORS.get(etype, "#AAAAAA")
        G.add_node(node_id, label=label, title=self._node_tooltip(ent),
                   color=color, shape="dot" if etype == "ex:LinguisticConcept" else "box")

    for rel in relations:
        subj = rel.get("subject", "")
        obj = rel.get("object", rel.get("obj", ""))
        pred = rel.get("predicate", "relatedTo")
        if subj and obj:
            edge_label = pred.split(":")[-1] if ":" in pred else pred
            G.add_edge(subj, obj, label=edge_label, title=pred)

    # ... pyvis rendering, G is discarded after .from_nx()
```

**SPARQL executor** (`src/queries.py:162–175`) — can be reused for health queries:

```python
def execute_sparql(ttl_code: str, query_str: str) -> pd.DataFrame:
    g = rdflib.Graph()
    try:
        g.parse(data=ttl_code, format="turtle")
        results = g.query(query_str)
        cols = [str(var) for var in results.vars]
        data = [[str(val) if val is not None else "" for val in row] for row in results]
        return pd.DataFrame(data, columns=cols)
    except Exception as e:
        return pd.DataFrame([{"Error": f"SPARQL Execution Failed: {str(e)}"}])
```

---

## 4. Consolidated Gap Summary

| # | Function/Module | Expected Location | Status | Severity |
|---|----------------|-------------------|--------|----------|
| 1 | `compute_hub_nodes` (centrality) | `triples.py` or `graph.py` | **MISSING** | Critical |
| 2 | Cognitive distillation filter (reframing paths) | `triples.py` | **MISSING** | Critical |
| 3 | IBIS/AIF parser functions | `semantics.py` | **FILE MISSING** | Critical |
| 4 | Markdown frontmatter → RDF mapping | `semantics.py` | **MISSING** | High |
| 5 | `#friction` → `ibis:Issue` binding | `semantics.py` | **MISSING** | High |
| 6 | Connectivity ratio computation | `health_diagnostics.py` | **DIR MISSING** | Critical |
| 7 | Discursive path traversal queries | `health_diagnostics.py` | **MISSING** | Critical |
| 8 | Graph topology inspection | `health_diagnostics.py` | **MISSING** | Critical |
| 9 | `ibis:reframes` SPARQL query | `queries.py` | **MISSING** | Medium |
| 10 | `OntologyGraph.prefixes` includes IBIS/AIF | `schemas.py` | **MISSING** (only in TripleGenerator) | Medium |
| 11 | Division-by-zero guards for centrality | N/A | **MISSING** | Medium |
| 12 | Concurrent `_entity_registry` safety | `triples.py` | **BUG** (shared class state) | Low |

---

## 5. Recommended Build Order

### Phase A: Foundation (build on existing code)
1. **Extract `networkx.DiGraph` construction** from `GraphBuilder._build_graph()` into a standalone `build_nx_graph(entities, relations) -> nx.DiGraph` function in a new `src/analytics/` package.
2. **Add IBIS/AIF/SKOS prefixes** to `OntologyGraph.prefixes` default in `schemas.py`.
3. **Fix the `_entity_registry` race condition** by making it instance-level (`self._entity_registry = {}` in `__init__`).

### Phase B: Centrality & Hub Detection (new `src/analytics/centrality.py`)
4. Implement `compute_hub_nodes(graph: nx.DiGraph, method="degree")` with degree, closeness, and betweenness centrality.
5. Add division-by-zero guards for disconnected components.
6. Implement `extract_reframing_paths(triples)` — filter for `ibis:reframes` / `ibis:resolves` edges.

### Phase C: Ontology Mapping (new `src/analytics/semantics.py`)
7. Implement `map_frontmatter_to_rdf(frontmatter: dict) -> List[Triple]` — deterministic parser for YAML frontmatter → RDF.
8. Implement `bind_friction_tags(tags: List[str]) -> List[Triple]` — `#friction` → `ibis:Issue`.
9. Implement `classify_speech_act(utterance: str) -> dict` — post-hoc verification that LLM edge assignments match prompt rules.

### Phase D: Health Diagnostics (new `src/analytics/health_diagnostics.py`)
10. Implement `compute_connectivity_ratio(graph: nx.DiGraph) -> float` with the mutually-reframing / isolated formula.
11. Implement `detect_siloing(graph: nx.DiGraph) -> dict` — identify disconnected components and their constituency.
12. Implement `compute_fragmentation_index(graph: nx.DiGraph) -> float`.
13. Add SPARQL queries for `ibis:reframes`, `ibis:endorses`, `aif:supports`/`aif:conflicts` to `queries.py`.

---

## 6. Code Snippets Ready for Hand-Off

The following existing code blocks are isolated and ready for the senior programmer to refine with docstrings, type annotations, and CLI wrappers:

1. **Entity normalization pipeline** — `triples.py:124–164` (`_normalize_label`, `_canonical_id`)
2. **Isolated-node binding algorithm** — `triples.py:238–280` (`_bind_isolated_nodes`)
3. **networkx DiGraph builder** — `graph.py:99–133` (`_build_graph` — extract networkx portion)
4. **SPARQL executor** — `queries.py:162–175` (`execute_sparql`)
5. **RDF-to-pyvis renderer** — `visualizer.py:108–185` (`render_rdf_graph`)
6. **MentalTool schema** — `schemas.py:399–491` (full MT_k data model)
7. **SYSTEM_PROMPT IBIS/AIF rules** — `prompts.py:46–82` (rules 11–15, invariants I–V)
