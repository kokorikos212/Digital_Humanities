"""
Talos RDF Graph Visualizer — parses Turtle/RDF strings and renders
self-contained PyVis interactive HTML network graphs.

Refactored from ``src/Talos/Talos_RDF_Viewer.py`` (Christophe Roche, 2025).
All Flask dependencies removed; single public API: ``render_rdf_graph()``.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS as _RDFS, OWL  # noqa: F401

# ── Namespaces ──────────────────────────────────────────────────────────────

RDFS_NS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OTV = Namespace("http://www.ontologia.fr/OTB/otv#")

# ── Colours ─────────────────────────────────────────────────────────────────

RELATION_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
    "#F8C471", "#82E0AA", "#F1948A", "#85CDFF", "#FFB347",
]

# ── Control panel (search, freeze, delete) ──────────────────────────────────

_CONTROL_PANEL = """
<div style="padding:10px;background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);border:1px solid #ddd;border-radius:8px;margin-bottom:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
    <input type="text" id="nodeSearch" placeholder="Search node (use * as wildcard)..."
      style="padding:6px 12px;border:1px solid #ccc;border-radius:4px;font-size:14px;min-width:200px;flex:1;max-width:300px;">
    <button onclick="searchNode()"
      style="padding:6px 12px;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px;">Search</button>
    <button onclick="resetAll()"
      style="padding:6px 12px;background:#2196F3;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px;">Reset</button>
    <button id="freezeBtn" onclick="toggleFreeze()"
      style="padding:6px 12px;background:#F5B027;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px;">Freeze (OFF)</button>
    <button onclick="deleteSelectedNode()"
      style="padding:6px 12px;background:#F54927;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px;">Delete node</button>
  </div>
</div>
<style>
  button:hover{opacity:0.8;transform:translateY(-1px);}
  #nodeSearch:focus{outline:none;border-color:#4CAF50;box-shadow:0 0 5px rgba(76,175,80,0.3);}
  body,html{margin:0;padding:0;height:100%;overflow:hidden;}
  #mynetwork{height:calc(100vh - 120px)!important;width:100%!important;}
</style>
<script>
  var isPhysicsEnabled=true;
  var isDragMode=false;
  function searchNode(){
    var pattern=document.getElementById('nodeSearch').value;
    if(!pattern){alert("Please enter a search term");return;}
    var matches=[];
    try{var regex=new RegExp(pattern.replace(/\\*/g,'.*'),'i');}
    catch(e){alert("Invalid expression: "+e.message);return;}
    network.body.data.nodes.forEach(function(node){
      if(regex.test(node.label)||regex.test(node.title)){
        matches.push(node.id);
        network.body.data.nodes.update({id:node.id,color:{background:'yellow'},font:{bold:true}});
      }
    });
    if(matches.length>0){network.selectNodes(matches);network.fit({nodes:matches,animation:true});alert(matches.length+" node(s) found");}
    else{alert("No matching nodes found.");}
  }
  function resetAll(){window.location.reload();}
  function deleteSelectedNode(){
    var selectedNodes=network.getSelectedNodes();
    if(selectedNodes.length===0){alert("Please select a node to delete");return;}
    if(selectedNodes.length>1){alert("Please select only one node to delete");return;}
    if(confirm("Delete this node and all its connections?")){
      network.body.data.edges.remove(network.getConnectedEdges(selectedNodes[0]));
      network.body.data.nodes.remove(selectedNodes[0]);
      network.redraw();
    }
  }
  function toggleFreeze(){
    var btn=document.getElementById('freezeBtn');
    isPhysicsEnabled=!isPhysicsEnabled;
    if(isPhysicsEnabled){
      network.setOptions({physics:{enabled:true,stabilization:{iterations:100}}});
      btn.innerHTML='Freeze (OFF)';btn.style.background='#F5B027';isDragMode=false;
      setTimeout(function(){network.fit({animation:{duration:1000,easingFunction:'easeInOutQuad'}});},200);
    }else{
      network.setOptions({physics:{enabled:false},edges:{smooth:{enabled:true,type:'straightCross',forceDirection:'none'}}});
      btn.innerHTML='Freeze (ON)';btn.style.background='#F44336';isDragMode=true;
      network.on('dragEnd',function(p){if(isDragMode&&p.nodes.length>0)network.redraw();});
      network.on('dragging',function(p){if(isDragMode&&p.nodes.length>0)network.redraw();});
    }
  }
  document.getElementById('nodeSearch').addEventListener('keypress',function(e){if(e.key==='Enter')searchNode();});
  network.once('stabilizationIterationsDone',function(){network.fit({animation:{duration:1000,easingFunction:'easeInOutQuad'}});});
  window.addEventListener('resize',function(){if(network){network.redraw();network.fit();}});
</script>
"""


# ── Public API ──────────────────────────────────────────────────────────────


def render_rdf_graph(ttl_data: str, height: str = "600px") -> str:
    """Parse a Turtle/RDF string and return a self-contained PyVis HTML string.

    Parameters
    ----------
    ttl_data:
        RDF data as a string (Turtle, XML, or JSON-LD).
    height:
        CSS height for the network container (e.g. ``"600px"``).

    Returns
    -------
    A complete ``<html>`` document with an interactive PyVis network graph,
    including search, freeze, and delete-node controls.
    """
    # ── Parse RDF ──────────────────────────────────────────────────────
    g = Graph()
    g.parse(data=ttl_data, format="turtle")

    # ── Identify node types (root / intermediate / terminal) ───────────
    all_subjects: set = set()
    all_objects: set = set()

    for s, _p, o in g:
        if isinstance(s, URIRef):
            all_subjects.add(str(s))
        if isinstance(o, URIRef):
            all_objects.add(str(o))

    root_nodes = all_subjects - all_objects
    terminal_nodes = all_objects - all_subjects

    # ── Build colour map per relation ──────────────────────────────────
    unique_relations = list({str(p) for _s, p, _o in g})
    relation_color_map = {
        rel: RELATION_COLORS[i % len(RELATION_COLORS)]
        for i, rel in enumerate(unique_relations)
    }

    # ── Build PyVis network ────────────────────────────────────────────
    from pyvis.network import Network

    net = Network(
        height=height, width="100%", directed=True,
        bgcolor="#ffffff", font_color="black",
    )
    net.toggle_physics(True)

    for s, p, o in g:
        s_label = _get_label(g, str(s)) if isinstance(s, URIRef) else _truncate(str(s))
        p_label = _short_name(str(p))
        edge_color = relation_color_map.get(str(p), "#808080")

        if isinstance(o, URIRef):
            o_label = _get_label(g, str(o))
            s_color = _node_color(str(s), root_nodes, terminal_nodes)
            o_color = _node_color(str(o), root_nodes, terminal_nodes)

            net.add_node(str(s), label=s_label, title=str(s), shape="ellipse", color=s_color)
            net.add_node(str(o), label=o_label, title=str(o), shape="ellipse", color=o_color)
            net.add_edge(str(s), str(o), label=p_label, title=str(p), color=edge_color)
        else:
            lit_id = f"{s_label}_{p_label}_{str(o)}"
            s_color = _node_color(str(s), root_nodes, terminal_nodes)

            net.add_node(str(s), label=s_label, title=str(s), shape="ellipse", color=s_color)
            net.add_node(lit_id, label=_truncate(str(o)), title=str(o), shape="box", color="#E0E0E0")
            net.add_edge(str(s), lit_id, label=p_label, title=str(p), color=edge_color)

    # ── Write to temp file and inject control panel ────────────────────
    output_path = os.path.join(tempfile.gettempdir(), "talos_graph.html")
    net.write_html(output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace('<div id="mynetwork"', _CONTROL_PANEL + '\n<div id="mynetwork"')
    return html


# ── Internal helpers ────────────────────────────────────────────────────────


def _truncate(label: str, max_len: int = 35) -> str:
    """Truncate label: first 15 + ... + last 15 characters."""
    if len(label) <= max_len:
        return label
    return label[:15] + "..." + label[-15:]


def _short_name(uri: str) -> str:
    """Return the final segment of a URI."""
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri:
        return uri.split("/")[-1]
    return uri


def _get_label(g: Graph, uri_str: str) -> str:
    """Resolve a human-readable label for a URI node."""
    uri = URIRef(uri_str)

    for short_name in g.objects(subject=uri, predicate=OTV.shortConceptName):
        return _truncate(str(short_name))

    for label in g.objects(subject=uri, predicate=RDFS_NS.label):
        return _truncate(str(label))

    return _truncate(_short_name(uri_str))


def _node_color(uri_str: str, roots: set, terminals: set) -> str:
    """Colour nodes by structural role."""
    if uri_str in roots:
        return "#87CEEB"
    if uri_str in terminals:
        return "#FFA07A"
    return "#DFF2FF"
