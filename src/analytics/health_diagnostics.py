r"""
Microdemocratic Health Evaluation & Discursive Path Analysis.

Structural integrity checks over the global directed multi-graph
:math:`\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{L})` produced by
the Talos ontology pipeline.  Computes connectivity ratios, detects
ideological siloing, and quantifies public-sphere fragmentation from
IBIS/AIF discourse graphs.

Core Metric — Connectivity Ratio
---------------------------------
.. math::

    \text{Ratio} = \frac{|\mathcal{V}_{\text{connected, mutually reframing}}|}
                        {|\mathcal{V}_{\text{isolated (degree-0)}}|}

where :math:`\mathcal{V}_{\text{connected, mutually reframing}}` is the set
of nodes reachable via :math:`\text{ibis:reframes}` or
:math:`\text{ibis:resolves}` edges, and
:math:`\mathcal{V}_{\text{isolated}}` is the set of degree-0 nodes.

A healthy deliberative graph exhibits a high ratio (many mutually-engaged
nodes, few isolates).  A low ratio indicates conversational noise,
ideological siloing, or public-sphere fragmentation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ── Custom Exceptions ───────────────────────────────────────────────────────


class GraphTopologyError(ValueError):
    """Raised when the graph topology is invalid for a requested computation.

    Examples: disconnected components for closeness centrality, empty
    graphs for connectivity analysis, or self-loop-only graphs.
    """


class EmptyCorpusError(ValueError):
    """Raised when the input corpus produces zero triples or an empty graph."""


class InvalidParameterError(ValueError):
    """Raised when a function receives a malformed or out-of-range parameter."""


# ── RDF → networkx Bridge ───────────────────────────────────────────────────


def build_nx_graph_from_rdf(
    rdf_source: Union[str, "rdflib.Graph"],  # noqa: F821
    format: str = "turtle",
) -> "nx.DiGraph":  # noqa: F821
    r"""Parse an RDF source into a `networkx.DiGraph`.

    Parameters
    ----------
    rdf_source:
        Either a Turtle / RDF string or an :class:`rdflib.Graph` instance.
    format:
        RDF serialization format (passed to :meth:`rdflib.Graph.parse`).
        Ignored when *rdf_source* is already an ``rdflib.Graph``.

    Returns
    -------
    nx.DiGraph
        A directed graph where each RDF triple :math:`(s, p, o)` becomes a
        directed edge *s* → *o* with the predicate *p* stored in the edge
        attribute ``predicate``.

    Raises
    ------
    EmptyCorpusError
        If the RDF source contains zero triples.
    InvalidParameterError
        If *rdf_source* is neither a string nor an ``rdflib.Graph``.

    Examples
    --------
    >>> from rdflib import Graph
    >>> g = Graph()
    >>> g.parse(data='@prefix ex: <http://example.org/> . ex:A ex:p ex:B .', format='turtle')
    >>> nxg = build_nx_graph_from_rdf(g)
    >>> nxg.number_of_nodes()
    2
    """
    import networkx as nx

    try:
        import rdflib
    except ImportError as exc:
        raise ImportError(
            "rdflib is required for RDF graph construction. "
            "Install it with: pip install rdflib"
        ) from exc

    if isinstance(rdf_source, rdflib.Graph):
        g = rdf_source
    elif isinstance(rdf_source, str):
        g = rdflib.Graph()
        try:
            g.parse(data=rdf_source, format=format)
        except Exception as exc:
            raise InvalidParameterError(
                f"Failed to parse RDF source as {format}: {exc}"
            ) from exc
    else:
        raise InvalidParameterError(
            f"rdf_source must be str or rdflib.Graph, got {type(rdf_source).__name__}"
        )

    if len(g) == 0:
        raise EmptyCorpusError("RDF graph contains zero triples.")

    G = nx.DiGraph()

    for s, p, o in g:
        s_str = str(s)
        o_str = str(o)
        p_str = str(p)

        # Node attributes
        if not G.has_node(s_str):
            G.add_node(s_str, is_uri=isinstance(s, rdflib.URIRef))
        if not G.has_node(o_str):
            G.add_node(o_str, is_uri=isinstance(o, rdflib.URIRef))

        G.add_edge(s_str, o_str, predicate=p_str)

    return G


# ── Connectivity Ratio ──────────────────────────────────────────────────────


def compute_connectivity_ratio(
    graph: "nx.DiGraph",  # noqa: F821
    reframing_predicates: Optional[List[str]] = None,
) -> float:
    r"""Compute the public-sphere health connectivity ratio.

    .. math::

        \text{Ratio} = \frac{|\mathcal{V}_{\text{connected, mutually reframing}}|}
                            {\max(1,\, |\mathcal{V}_{\text{isolated (degree-0)}}|)}

    Nodes are *mutually reframing* if they participate in at least one edge
    whose predicate matches an ``ibis:reframes`` or ``ibis:resolves`` CURIE.

    Parameters
    ----------
    graph:
        A :class:`networkx.DiGraph` representing the RDF discourse graph.
    reframing_predicates:
        Predicate CURIE strings that qualify as "reframing" edges.
        Defaults to ``["ibis:reframes", "ibis:resolves"]``.

    Returns
    -------
    float
        The connectivity ratio.  Returns :obj:`math.inf` when there are
        **zero** isolated nodes (perfect connectivity).  Returns ``0.0``
        when there are **zero** mutually-reframing nodes.

    Raises
    ------
    GraphTopologyError
        If the graph is empty (zero nodes).

    Examples
    --------
    >>> import networkx as nx
    >>> G = nx.DiGraph()
    >>> G.add_edge("ex:A", "ex:B", predicate="ibis:reframes")
    >>> G.add_edge("ex:C", "ex:D", predicate="rdf:type")
    >>> ratio = compute_connectivity_ratio(G)
    >>> ratio > 0
    True
    """
    import math

    if reframing_predicates is None:
        reframing_predicates = [
            "http://purl.org/ibis#reframes",
            "ibis:reframes",
            "http://purl.org/ibis#resolves",
            "ibis:resolves",
        ]

    if graph.number_of_nodes() == 0:
        raise GraphTopologyError("Cannot compute connectivity ratio on an empty graph.")

    # ── Mutually-reframing nodes ────────────────────────────────────────
    mutually_reframing: set = set()
    for u, v, data in graph.edges(data=True):
        pred = data.get("predicate", "")
        if any(rp in pred for rp in reframing_predicates):
            mutually_reframing.add(u)
            mutually_reframing.add(v)

    # ── Isolated (degree-0) nodes ───────────────────────────────────────
    isolated: set = {
        node
        for node in graph.nodes()
        if graph.degree(node) == 0
    }

    if len(isolated) == 0:
        # Perfect connectivity — every node has at least one edge
        return math.inf if len(mutually_reframing) > 0 else 0.0

    return len(mutually_reframing) / len(isolated)


# ── Siloing Detection ───────────────────────────────────────────────────────


def detect_siloing(
    graph: "nx.DiGraph",  # noqa: F821
) -> Dict[str, Any]:
    r"""Detect ideological siloing via weakly-connected component analysis.

    A *silo* is a weakly-connected component (WCC) of size ≥ 2 that has
    **zero** ``ibis:reframes``, ``ibis:resolves``, ``aif:supports``, or
    ``aif:conflicts`` edges crossing to another component.  Such components
    represent echo chambers where deliberation cannot penetrate.

    Parameters
    ----------
    graph:
        A :class:`networkx.DiGraph` representing the RDF discourse graph.

    Returns
    -------
    dict
        Keys:

        - ``total_components`` (:class:`int`) — number of weakly-connected
          components.
        - ``siloed_components`` (:class:`int`) — components with no
          cross-component deliberative edges.
        - ``silo_sizes`` (:class:`list`) — node counts per siloed component.
        - ``largest_silo_pct`` (:class:`float`) — percentage of total nodes
          in the largest silo.
        - ``is_healthy`` (:class:`bool`) — ``True`` if the graph is a single
          component with no siloing.

    Raises
    ------
    GraphTopologyError
        If the graph is empty.

    Examples
    --------
    >>> import networkx as nx
    >>> G = nx.DiGraph()
    >>> G.add_edge("ex:A", "ex:B", predicate="ibis:rebuts")
    >>> G.add_edge("ex:C", "ex:C", predicate="rdfs:label")  # self-loop, isolated component
    >>> result = detect_siloing(G)
    >>> result["total_components"] >= 1
    True
    """
    import networkx as nx

    if graph.number_of_nodes() == 0:
        raise GraphTopologyError("Cannot detect siloing on an empty graph.")

    bridging_predicates = {
        "ibis:reframes",
        "http://purl.org/ibis#reframes",
        "ibis:resolves",
        "http://purl.org/ibis#resolves",
        "aif:supports",
        "http://www.arg.tech/aif#supports",
        "aif:conflicts",
        "http://www.arg.tech/aif#conflicts",
    }

    # Weakly-connected components
    wccs = list(nx.weakly_connected_components(graph))
    total_nodes = graph.number_of_nodes()

    # Build component index: node → component_id
    node_to_comp: Dict[Any, int] = {}
    for idx, comp in enumerate(wccs):
        for node in comp:
            node_to_comp[node] = idx

    # A single-component graph is trivially healthy (no cross-component
    # bridging is *needed* — everything is already in one component).
    if len(wccs) == 1:
        return {
            "total_components": 1,
            "siloed_components": 0,
            "silo_sizes": [],
            "largest_silo_pct": 0.0,
            "is_healthy": True,
        }

    # Check each component for bridging edges to other components
    siloed: List[set] = []
    for idx, comp in enumerate(wccs):
        if len(comp) < 2:
            continue  # single-node components aren't "silos" — they're isolates
        has_bridge = False
        for node in comp:
            for _, neighbor, data in graph.out_edges(node, data=True):
                if node_to_comp.get(neighbor, idx) != idx:
                    pred = data.get("predicate", "")
                    if any(bp in pred for bp in bridging_predicates):
                        has_bridge = True
                        break
            if has_bridge:
                break
        if not has_bridge:
            siloed.append(comp)

    silo_sizes = sorted([len(c) for c in siloed], reverse=True)
    largest_silo_pct = (silo_sizes[0] / total_nodes * 100) if silo_sizes else 0.0

    return {
        "total_components": len(wccs),
        "siloed_components": len(siloed),
        "silo_sizes": silo_sizes,
        "largest_silo_pct": round(largest_silo_pct, 2),
        "is_healthy": len(wccs) == 1 and len(siloed) == 0,
    }


# ── Fragmentation Index ─────────────────────────────────────────────────────


def compute_fragmentation_index(
    graph: "nx.DiGraph",  # noqa: F821
) -> float:
    r"""Compute the public-sphere fragmentation index.

    .. math::

        F = 1 - \frac{|\mathcal{C}_{\text{max}}|}{|\mathcal{V}|}

    where :math:`|\mathcal{C}_{\text{max}}|` is the size of the largest
    weakly-connected component and :math:`|\mathcal{V}|` is the total number
    of nodes.

    A value of ``0.0`` means a fully-connected graph (no fragmentation).
    A value approaching ``1.0`` means severe fragmentation (many isolated
    nodes or small disconnected clusters).

    Parameters
    ----------
    graph:
        A :class:`networkx.DiGraph` representing the RDF discourse graph.

    Returns
    -------
    float
        Fragmentation index :math:`F \in [0, 1]`.

    Raises
    ------
    GraphTopologyError
        If the graph is empty.

    Examples
    --------
    >>> import networkx as nx
    >>> G = nx.DiGraph()
    >>> G.add_edge("A", "B")
    >>> G.add_edge("B", "C")
    >>> idx = compute_fragmentation_index(G)
    >>> 0.0 <= idx <= 1.0
    True
    """
    import networkx as nx

    if graph.number_of_nodes() == 0:
        raise GraphTopologyError("Cannot compute fragmentation index on an empty graph.")

    total = graph.number_of_nodes()
    wccs = list(nx.weakly_connected_components(graph))
    largest = max(len(c) for c in wccs) if wccs else 0

    return 1.0 - (largest / total)


# ── Comprehensive Health Report ──────────────────────────────────────────────


def graph_health_report(
    rdf_source: Union[str, "rdflib.Graph"],  # noqa: F821
    format: str = "turtle",
) -> Dict[str, Any]:
    r"""Produce a comprehensive microdemocratic health report for an RDF graph.

    Parameters
    ----------
    rdf_source:
        A Turtle / RDF string or an :class:`rdflib.Graph` instance.
    format:
        RDF serialization format.  Ignored when *rdf_source* is already a
        ``rdflib.Graph``.

    Returns
    -------
    dict
        Keys:

        - ``total_nodes``, ``total_edges`` — graph size.
        - ``connectivity_ratio`` — the mutually-reframing / isolated ratio.
        - ``fragmentation_index`` — :math:`F \in [0, 1]`.
        - ``siloing`` — the full :func:`detect_siloing` result dict.
        - ``isolated_node_count`` — number of degree-0 nodes.
        - ``mutually_reframing_count`` — number of nodes on reframing edges.
        - ``health_verdict`` — one of ``"healthy"``, ``"fragmented"``,
          ``"siloed"``, ``"empty"``.

        Returns a **fallback** dictionary of zeroes when the input produces
        zero triples (no exception raised — a warning is logged instead).

    Examples
    --------
    >>> from rdflib import Graph
    >>> g = Graph()
    >>> g.parse(data='''
    ... @prefix ex: <http://example.org/> .
    ... @prefix ibis: <http://purl.org/ibis#> .
    ... ex:A ibis:reframes ex:B .
    ... ''', format='turtle')
    >>> report = graph_health_report(g)
    >>> report["total_nodes"]
    2
    """
    import math

    try:
        G = build_nx_graph_from_rdf(rdf_source, format=format)
    except EmptyCorpusError:
        logger.warning(
            "Empty RDF graph — returning fallback health report with default zeroes."
        )
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "connectivity_ratio": 0.0,
            "fragmentation_index": 0.0,
            "siloing": {
                "total_components": 0,
                "siloed_components": 0,
                "silo_sizes": [],
                "largest_silo_pct": 0.0,
                "is_healthy": True,
            },
            "isolated_node_count": 0,
            "mutually_reframing_count": 0,
            "health_verdict": "empty",
        }

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    # Isolated nodes
    isolated_count = sum(1 for n in G.nodes() if G.degree(n) == 0)

    # Mutually-reframing nodes
    reframing_preds = {
        "ibis:reframes", "http://purl.org/ibis#reframes",
        "ibis:resolves", "http://purl.org/ibis#resolves",
    }
    mutually_reframing: set = set()
    for u, v, data in G.edges(data=True):
        pred = data.get("predicate", "")
        if any(rp in pred for rp in reframing_preds):
            mutually_reframing.add(u)
            mutually_reframing.add(v)

    # Connectivity ratio (guarded)
    try:
        conn_ratio = compute_connectivity_ratio(G)
    except GraphTopologyError:
        conn_ratio = 0.0

    # Fragmentation
    try:
        frag = compute_fragmentation_index(G)
    except GraphTopologyError:
        frag = 0.0

    # Siloing
    try:
        siloing = detect_siloing(G)
    except GraphTopologyError:
        siloing = {
            "total_components": 0,
            "siloed_components": 0,
            "silo_sizes": [],
            "largest_silo_pct": 0.0,
            "is_healthy": True,
        }

    # Verdict
    if total_nodes == 0:
        verdict = "empty"
    elif siloing["siloed_components"] > 0:
        verdict = "siloed"
    elif frag > 0.5:
        verdict = "fragmented"
    else:
        verdict = "healthy"

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "connectivity_ratio": conn_ratio if not math.isinf(conn_ratio) else float(total_nodes),
        "fragmentation_index": round(frag, 6),
        "siloing": siloing,
        "isolated_node_count": isolated_count,
        "mutually_reframing_count": len(mutually_reframing),
        "health_verdict": verdict,
    }
