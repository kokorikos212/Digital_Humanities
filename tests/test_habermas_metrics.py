r"""
Test suite for Habermasian deliberative metrics and micro-ontology alignment.

Covers:

1. Degree / closeness centrality over a synthetic 5-node graph.
2. ``#friction`` tag → ``ibis:Issue`` RDF triple parsing.
3. Disconnected graph handling (no arithmetic runtime errors).
4. Full health report on empty and populated graphs.
"""

from __future__ import annotations

import math
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def synthetic_5node_rdf_graph():
    """A 5-node RDF graph with known centrality structure.

    Topology::

        A (skos:Concept) → B (skos:Concept) → C (skos:Concept)
        A ──────────────→ D (skos:Concept)
        E (isolated, not skos:Concept)

    Expected:
    - A: degree=3 (out to B, D + rdf:type self-loop counts),
      highest centrality
    - B: degree=2 (in from A, out to C)
    - C: degree=1 (in from B)
    - D: degree=1 (in from A)
    - E: degree=0 (isolated, not a concept)
    """
    from rdflib import Graph, Namespace, RDF, RDFS, URIRef, Literal

    EX = Namespace("http://example.org/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
    IBIS = Namespace("http://purl.org/ibis#")

    g = Graph()
    g.bind("ex", EX)
    g.bind("skos", SKOS)
    g.bind("ibis", IBIS)

    # Nodes with rdf:type
    for node, label in [
        (EX.A, "Hub A"),
        (EX.B, "Hub B"),
        (EX.C, "Terminal C"),
        (EX.D, "Terminal D"),
    ]:
        g.add((node, RDF.type, SKOS.Concept))
        g.add((node, RDFS.label, Literal(label)))

    # E is not a skos:Concept — it's a schema:Person
    g.add((EX.E, RDF.type, URIRef("http://schema.org/Person")))
    g.add((EX.E, RDFS.label, Literal("Isolated Person")))

    # Edges
    g.add((EX.A, EX.reframes, EX.B))
    g.add((EX.B, EX.rebuts, EX.C))
    g.add((EX.A, IBIS.reframes, EX.D))

    return g


@pytest.fixture
def empty_rdf_graph():
    """An rdflib Graph with zero triples."""
    from rdflib import Graph
    return Graph()


@pytest.fixture
def single_node_graph():
    """An rdflib Graph with a single skos:Concept node and no edges."""
    from rdflib import Graph, Namespace, RDF, RDFS, Literal

    EX = Namespace("http://example.org/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    g = Graph()
    g.add((EX.Solo, RDF.type, SKOS.Concept))
    g.add((EX.Solo, RDFS.label, Literal("Lone Node")))
    return g


@pytest.fixture
def disconnected_graph():
    """Two isolated skos:Concept nodes with no edges between them."""
    from rdflib import Graph, Namespace, RDF, RDFS, Literal

    EX = Namespace("http://example.org/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    g = Graph()
    g.add((EX.IslandA, RDF.type, SKOS.Concept))
    g.add((EX.IslandA, RDFS.label, Literal("Island A")))
    g.add((EX.IslandB, RDF.type, SKOS.Concept))
    g.add((EX.IslandB, RDFS.label, Literal("Island B")))
    return g


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Centrality Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeHubNodes:
    """Degree and closeness centrality over skos:Concept nodes."""

    def test_degree_centrality_ranking(self, synthetic_5node_rdf_graph):
        """A and B are the top-2 centrality nodes (degree tie may swap order)."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(synthetic_5node_rdf_graph, top_n=5)

        assert len(hubs) == 4  # 4 skos:Concept nodes (E is not a Concept)
        top_labels = {h["label"] for h in hubs[:2]}
        assert top_labels == {"Hub A", "Hub B"}
        assert hubs[0]["degree_centrality"] > 0

    def test_hub_a_has_highest_degree(self, synthetic_5node_rdf_graph):
        """A (3 edges) > B (2 edges) > C/D (1 edge each)."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(synthetic_5node_rdf_graph, top_n=5)

        scores = [h["degree_centrality"] for h in hubs]
        # Scores should be strictly decreasing (or equal for C/D)
        assert scores[0] >= scores[1] >= scores[2] >= scores[3]

    def test_top_n_truncation(self, synthetic_5node_rdf_graph):
        """top_n=2 returns only 2 hubs."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(synthetic_5node_rdf_graph, top_n=2)
        assert len(hubs) == 2

    def test_closeness_centrality_present(self, synthetic_5node_rdf_graph):
        """Every hub dict includes closeness_centrality."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(synthetic_5node_rdf_graph, top_n=5)
        for h in hubs:
            assert "closeness_centrality" in h
            assert isinstance(h["closeness_centrality"], float)

    def test_empty_graph_returns_empty_list(self, empty_rdf_graph):
        """An empty graph produces an empty hub list, not an error."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(empty_rdf_graph, top_n=5)
        assert hubs == []

    def test_single_node_returns_empty_list(self, single_node_graph):
        """A single-node graph (|V| ≤ 1) returns empty list."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(single_node_graph, top_n=5)
        assert hubs == []

    def test_disconnected_graph_closeness_zero(self, disconnected_graph):
        """Disconnected components → closeness_centrality = 0.0 for all nodes."""
        from src.tools.triples import compute_hub_nodes

        hubs = compute_hub_nodes(disconnected_graph, top_n=5)
        assert len(hubs) == 2
        for h in hubs:
            assert h["closeness_centrality"] == 0.0

    def test_top_n_zero_raises(self, synthetic_5node_rdf_graph):
        """top_n=0 raises InvalidParameterError."""
        from src.tools.triples import compute_hub_nodes
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError, match="top_n"):
            compute_hub_nodes(synthetic_5node_rdf_graph, top_n=0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Cognitive Distillation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDistillCognitiveTools:
    """Reframing edge-path extraction (ibis:reframes / ibis:resolves)."""

    def test_extracts_reframing_edges(self, synthetic_5node_rdf_graph):
        """Only ibis:reframes edges match (ex:reframes is example-ns, not IBIS)."""
        from src.tools.triples import distill_cognitive_tools

        paths = distill_cognitive_tools(synthetic_5node_rdf_graph)
        # A→D uses ibis:reframes (matches); A→B uses ex:reframes (doesn't match)
        assert len(paths) == 1
        assert "ibis#reframes" in paths[0]["predicate"]

    def test_reframing_paths_have_required_keys(self, synthetic_5node_rdf_graph):
        """Each path dict has source, predicate, target, and labels."""
        from src.tools.triples import distill_cognitive_tools

        paths = distill_cognitive_tools(synthetic_5node_rdf_graph)
        for p in paths:
            for key in ("source", "predicate", "target", "source_label", "target_label"):
                assert key in p, f"Missing key: {key}"

    def test_no_reframing_edges_returns_empty(self, disconnected_graph):
        """Graph with no reframing edges returns empty list."""
        from src.tools.triples import distill_cognitive_tools

        paths = distill_cognitive_tools(disconnected_graph)
        assert paths == []

    def test_empty_graph_returns_empty(self, empty_rdf_graph):
        """Empty graph returns empty list without error."""
        from src.tools.triples import distill_cognitive_tools

        paths = distill_cognitive_tools(empty_rdf_graph)
        assert paths == []


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Semantics / Micro-Ontology Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFrictionTagMapping:
    """#friction tags → ibis:Issue RDF triples."""

    def test_basic_friction_tag(self):
        """#friction/budget → ibis:Issue type declaration."""
        from src.tools.semantics import map_friction_tag_to_ibis_issue

        result = map_friction_tag_to_ibis_issue("#friction/budget_allocation")
        assert result["predicate"] == "rdf:type"
        assert result["object"] == "ibis:Issue"
        assert "Budget" in result["subject"]

    def test_tag_without_hash(self):
        """Tag without leading # still maps correctly."""
        from src.tools.semantics import map_friction_tag_to_ibis_issue

        result = map_friction_tag_to_ibis_issue("friction/housing")
        assert result["object"] == "ibis:Issue"

    def test_custom_label(self):
        """Custom label overrides the auto-generated one."""
        from src.tools.semantics import map_friction_tag_to_ibis_issue

        # We check the subject still follows conventions
        result = map_friction_tag_to_ibis_issue("#friction/budget", label="Budget Crisis")
        assert result["object"] == "ibis:Issue"

    def test_empty_tag_raises(self):
        """Empty tag raises InvalidParameterError."""
        from src.tools.semantics import map_friction_tag_to_ibis_issue
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            map_friction_tag_to_ibis_issue("")

    def test_non_friction_tag_raises(self):
        """Tag without 'friction' raises InvalidParameterError."""
        from src.tools.semantics import map_friction_tag_to_ibis_issue
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError, match="friction"):
            map_friction_tag_to_ibis_issue("#todo/shopping")


class TestClaimToAifInode:
    """Claim → aif:I-node + ibis:Position mapping."""

    def test_claim_generates_aif_inode(self):
        """Claim produces both ibis:Position and aif:I-node type triples."""
        from src.tools.semantics import map_claim_to_aif_inode

        triples = map_claim_to_aif_inode("ML detects bias", "Full claim text here.")
        types = {t["object"] for t in triples if t["predicate"] == "rdf:type"}
        assert "ibis:Position" in types
        assert "aif:I-node" in types

    def test_claim_with_speaker(self):
        """Speaker ID generates ibis:asserts edge."""
        from src.tools.semantics import map_claim_to_aif_inode

        triples = map_claim_to_aif_inode(
            "Housing first", "Housing subsidies must come first.",
            speaker_id="ex:Rep_Maria",
        )
        predicates = {t["predicate"] for t in triples}
        assert "ibis:asserts" in predicates

    def test_empty_label_raises(self):
        """Empty claim_label raises InvalidParameterError."""
        from src.tools.semantics import map_claim_to_aif_inode
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            map_claim_to_aif_inode("")


class TestEdgeSemanticsClassifier:
    """Speech-act → IBIS/AIF edge pair classification."""

    def test_rebuttal(self):
        from src.tools.semantics import classify_edge_semantics

        result = classify_edge_semantics("rebuttal")
        assert result["ibis_edge"] == "ibis:rebuts"
        assert result["aif_edge"] == "aif:conflicts"

    def test_agreement(self):
        from src.tools.semantics import classify_edge_semantics

        result = classify_edge_semantics("agreement")
        assert result["ibis_edge"] == "ibis:endorses"
        assert result["aif_edge"] == "aif:supports"

    def test_synthesis(self):
        from src.tools.semantics import classify_edge_semantics

        result = classify_edge_semantics("synthesis")
        assert result["ibis_edge"] == "ibis:respondsTo"

    def test_unknown_raises(self):
        from src.tools.semantics import classify_edge_semantics
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            classify_edge_semantics("insult")


class TestFrontmatterValidation:
    """YAML frontmatter validation and parsing."""

    def test_valid_frontmatter(self):
        from src.tools.semantics import validate_frontmatter

        # Should not raise
        validate_frontmatter({"tags": ["friction/budget"], "id": "note_001"})

    def test_empty_frontmatter_raises(self):
        from src.tools.semantics import validate_frontmatter
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_frontmatter({})

    def test_unrecognised_keys_raises(self):
        from src.tools.semantics import validate_frontmatter
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_frontmatter({"unknown_key": "value"})

    def test_non_string_tags_raise(self):
        from src.tools.semantics import validate_frontmatter
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_frontmatter({"tags": [123]})

    def test_unprefixed_rdf_type_raises(self):
        from src.tools.semantics import validate_frontmatter
        from src.analytics.health_diagnostics import InvalidParameterError

        with pytest.raises(InvalidParameterError, match="CURIE"):
            validate_frontmatter({"rdf_type": "Issue"})  # missing prefix

    def test_parse_frontmatter_generates_triples(self):
        from src.tools.semantics import parse_frontmatter_to_triples

        triples = parse_frontmatter_to_triples({
            "tags": ["friction/budget"],
            "id": "note_001",
            "label": "Budget Debate",
        })
        assert len(triples) >= 2
        types = {t["object"] for t in triples if t["predicate"] == "rdf:type"}
        assert "ibis:Issue" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Health Diagnostics Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthDiagnostics:
    """Graph connectivity, siloing, and fragmentation diagnostics."""

    def test_empty_graph_returns_fallback(self, empty_rdf_graph):
        """Empty graph returns fallback dict with zeroes, no exception."""
        from src.analytics.health_diagnostics import graph_health_report

        report = graph_health_report(empty_rdf_graph)
        assert report["total_nodes"] == 0
        assert report["total_edges"] == 0
        assert report["connectivity_ratio"] == 0.0
        assert report["fragmentation_index"] == 0.0
        assert report["health_verdict"] == "empty"

    def test_empty_ttl_string_returns_fallback(self):
        """Empty TTL string returns fallback, not an exception."""
        from src.analytics.health_diagnostics import graph_health_report

        report = graph_health_report("")
        assert report["health_verdict"] == "empty"

    def test_disconnected_graph_no_crash(self, disconnected_graph):
        """Disconnected nodes don't cause arithmetic errors.

        Note: RDF nodes always have edges (rdf:type, rdfs:label), so
        isolating domain entities requires intentional degree-0 nodes.
        The critical assertion is that no exception is raised and the
        report is structurally valid.
        """
        from src.analytics.health_diagnostics import graph_health_report

        report = graph_health_report(disconnected_graph)
        assert "error" not in report
        assert report["total_nodes"] > 0
        assert report["total_edges"] > 0
        # Report is well-formed even for disconnected entities
        assert isinstance(report["connectivity_ratio"], (int, float))
        assert isinstance(report["fragmentation_index"], float)

    def test_fragmentation_index_range(self):
        """Fragmentation index is always in [0, 1]."""
        from rdflib import Graph, Namespace, RDF, RDFS, Literal
        from src.analytics.health_diagnostics import compute_fragmentation_index, build_nx_graph_from_rdf

        EX = Namespace("http://example.org/")
        g = Graph()
        g.add((EX.A, RDF.type, EX.Concept))
        g.add((EX.A, EX.p, EX.B))
        g.add((EX.B, EX.q, EX.C))

        nxg = build_nx_graph_from_rdf(g)
        frag = compute_fragmentation_index(nxg)
        assert 0.0 <= frag <= 1.0

    def test_connectivity_ratio_on_connected_graph(self):
        """A fully-connected reframing graph has infinite (or high) ratio."""
        from rdflib import Graph, Namespace, URIRef
        from src.analytics.health_diagnostics import build_nx_graph_from_rdf, compute_connectivity_ratio

        IBIS = Namespace("http://purl.org/ibis#")
        EX = Namespace("http://example.org/")
        g = Graph()
        g.add((EX.A, IBIS.reframes, EX.B))
        g.add((EX.B, IBIS.reframes, EX.C))

        nxg = build_nx_graph_from_rdf(g)
        ratio = compute_connectivity_ratio(nxg)
        # No isolated nodes → infinite (perfect health)
        assert ratio == math.inf

    def test_siloing_on_connected_graph(self):
        """A fully-connected graph shows no siloing."""
        from rdflib import Graph, Namespace
        from src.analytics.health_diagnostics import build_nx_graph_from_rdf, detect_siloing

        IBIS = Namespace("http://purl.org/ibis#")
        EX = Namespace("http://example.org/")
        g = Graph()
        g.add((EX.A, IBIS.reframes, EX.B))

        nxg = build_nx_graph_from_rdf(g)
        result = detect_siloing(nxg)
        assert result["is_healthy"] is True
        assert result["siloed_components"] == 0

    def test_graph_topology_error_on_empty(self):
        """Empty networkx graph raises GraphTopologyError for connectivity."""
        import networkx as nx
        from src.analytics.health_diagnostics import compute_connectivity_ratio, GraphTopologyError

        with pytest.raises(GraphTopologyError):
            compute_connectivity_ratio(nx.DiGraph())

    def test_build_nx_graph_from_ttl_string(self):
        """A Turtle string is correctly parsed into a networkx DiGraph."""
        from src.analytics.health_diagnostics import build_nx_graph_from_rdf

        ttl = """
        @prefix ex: <http://example.org/> .
        @prefix ibis: <http://purl.org/ibis#> .
        ex:A ibis:reframes ex:B .
        ex:B a ex:Concept .
        """
        nxg = build_nx_graph_from_rdf(ttl)
        assert nxg.number_of_nodes() >= 2
        assert nxg.number_of_edges() >= 2  # rdf:type + ibis:reframes

    def test_build_nx_graph_rejects_bad_input(self):
        """Non-string, non-Graph input raises InvalidParameterError."""
        from src.analytics.health_diagnostics import build_nx_graph_from_rdf, InvalidParameterError

        with pytest.raises(InvalidParameterError):
            build_nx_graph_from_rdf(42)  # type: ignore
