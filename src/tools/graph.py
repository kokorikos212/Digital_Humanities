"""
Graph Builder — creates semantic network visualizations from ontological
entities and relations using networkx + pyvis.

Produces an interactive HTML graph where nodes are entities and edges
are the triples/relations connecting them.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from src.config import config


# ── Input schema ──────────────────────────────────────────────────────────


class GraphBuilderInput(BaseModel):
    """Input for building a semantic graph visualization."""

    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Entity dicts: {id, label, rdf_type, properties, …}",
    )
    relations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relation / triple dicts: {subject, predicate, object}",
    )
    title: str = Field(
        "Semantic Network", description="Graph title displayed at the top"
    )
    layout: Literal["hierarchical", "force_atlas", "radial"] = Field(
        "force_atlas", description="Layout algorithm for the graph"
    )


# ── Tool implementation ───────────────────────────────────────────────────


class GraphBuilder:
    """Build interactive semantic-network visualizations with networkx + pyvis."""

    TYPE_COLORS: Dict[str, str] = {
        "ex:Conversation": "#4A90D9",
        "ex:Utterance": "#7B9CC2",
        "ex:Speaker": "#E8913A",
        "ex:NamedEntity": "#50B86C",
        "ex:LinguisticConcept": "#9B59B6",
        "ex:PragmaticFeature": "#E74C3C",
        "ex:DependencyRelation": "#95A5A6",
        "ex:DiscourseMarker": "#F39C12",
        "rdf:type": "#34495E",
    }

    def __init__(self):
        config.ensure_output_dirs()

    # ── Public tool method ────────────────────────────────────────────

    def generate_semantic_graph(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        title: str = "Semantic Network",
        layout: str = "force_atlas",
    ) -> Dict[str, Any]:
        """Build and save an interactive semantic-network HTML file.

        Returns a dict with ``saved_at``, ``node_count``, ``edge_count``,
        and a ``summary`` string.
        """
        graph_data = self._build_graph(entities, relations, title, layout)

        timestamp = int(time.time())
        safe_title = title.replace(" ", "_").lower()[:40]
        filename = f"semantic_{safe_title}_{timestamp}.html"
        filepath = str(config.graphs_dir / filename)

        graph_data["html"].write_html(filepath, open_browser=False)

        return {
            "saved_at": filepath,
            "node_count": graph_data["node_count"],
            "edge_count": graph_data["edge_count"],
            "summary": (
                f"Semantic network '{title}': "
                f"{graph_data['node_count']} nodes, "
                f"{graph_data['edge_count']} edges."
            ),
        }

    # ── Graph construction ────────────────────────────────────────────

    def _build_graph(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        title: str,
        layout: str,
    ) -> Dict[str, Any]:
        """Construct the networkx graph and wrap it in pyvis."""
        import networkx as nx
        from pyvis.network import Network

        G = nx.DiGraph()

        for ent in entities:
            node_id = ent.get("id", ent.get("label", str(hash(str(ent)))))
            label = ent.get("label", node_id)
            etype = ent.get("rdf_type", ent.get("entity_type", "ex:Concept"))
            color = self.TYPE_COLORS.get(etype, "#AAAAAA")

            G.add_node(
                node_id,
                label=label,
                title=self._node_tooltip(ent),
                color=color,
                shape="dot" if etype == "ex:LinguisticConcept" else "box",
            )

        for rel in relations:
            subj = rel.get("subject", "")
            obj = rel.get("object", rel.get("obj", ""))
            pred = rel.get("predicate", "relatedTo")

            if subj and obj:
                edge_label = pred.split(":")[-1] if ":" in pred else pred
                G.add_edge(subj, obj, label=edge_label, title=pred)

        net = Network(
            height="700px",
            width="100%",
            directed=True,
            notebook=False,
            cdn_resources="in_line",
        )
        net.from_nx(G)

        physics_config: Dict[str, Any] = {
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08,
            },
            "stabilization": {"iterations": 150},
        }
        if layout == "hierarchical":
            physics_config = {
                "solver": "hierarchicalRepulsion",
                "hierarchicalRepulsion": {
                    "centralGravity": 0.0,
                    "springLength": 200,
                    "springConstant": 0.01,
                    "nodeDistance": 120,
                },
            }

        options = {
            "physics": physics_config,
            "nodes": {
                "font": {"size": 14, "face": "sans-serif"},
                "borderWidth": 2,
            },
            "edges": {
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
                "font": {"size": 11, "face": "sans-serif", "strokeWidth": 0},
                "smooth": {"type": "continuous"},
            },
            "interaction": {
                "hover": True,
                "tooltipDelay": 100,
                "navigationButtons": True,
            },
        }
        net.set_options(json.dumps(options))

        return {
            "html": net,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "graph": G,
        }

    @staticmethod
    def _node_tooltip(entity: Dict[str, Any]) -> str:
        """Build an HTML tooltip string for a node."""
        lines = [f"<b>{entity.get('label', entity.get('id', '?'))}</b>"]
        etype = entity.get("rdf_type", entity.get("entity_type", ""))
        if etype:
            lines.append(f"<br/>Type: {etype}")
        props = entity.get("properties", {})
        for k, v in props.items():
            short_k = k.split(":")[-1] if ":" in k else k
            lines.append(f"<br/>{short_k}: {v}")
        return "".join(lines)


# ── Registry helpers ──────────────────────────────────────────────────────

graph_builder_registry = [
    ("generate_semantic_graph", GraphBuilderInput),
]
