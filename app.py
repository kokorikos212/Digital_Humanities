#!/usr/bin/env python3
"""
Gradio Web UI for the Ontological Conversation Analysis Pipeline.

Features:
  - Dynamic tool selection (checkbox group) — only selected tools execute
  - Text input + pre-loaded example selector
  - Tabbed output: JSON summary, Turtle RDF, semantic graph, Obsidian notes
  - Designed for iframe embedding in GitHub Pages

Usage:
    python app.py                 # launch locally
    python app.py --share         # create a public Gradio link
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set

import os
os.environ["GRADIO_SERVER_NAME"] = "0.0.0.0"
os.environ["GRADIO_SERVER_PORT"] = "7860"

import gradio as gr

# Monkey-patch: Gradio 4.44.1 gr.File crashes _json_schema_to_python_type on bool
import gradio_client.utils as _gcu
_orig_json_schema = _gcu._json_schema_to_python_type
def _safe_json_schema(schema, defs=None):
    if isinstance(schema, bool):
        return "Any"
    try:
        return _orig_json_schema(schema, defs)
    except TypeError:
        return "Any"
_gcu._json_schema_to_python_type = _safe_json_schema

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import html as _html

from src.config import config
from src.pipeline import run_pipeline
from src.prompts import get_system_prompt, NAMED_PROMPTS, build_analysis_prompt
from src.tools import TOOL_UI_LABELS
from src.visualizer import render_rdf_graph
from src.queries import PRESET_SPARQL_QUERIES, CASE_QUERIES, execute_sparql, get_queries_for_case
from src.precomputed import load_precomputed_asset, PRECOMPUTED_MAP
from src.ingestion import save_uploaded_files

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

EXAMPLES = NAMED_PROMPTS

DEFAULT_EXAMPLE = "bench_1_1_rebuttal"

# ═══════════════════════════════════════════════════════════════════════════
# Pipeline runner
# ═══════════════════════════════════════════════════════════════════════════


def run_analysis(
    text: str,
    enable_linguistics: bool,
    enable_triples: bool,
    enable_graph: bool,
    enable_obsidian: bool,
    enable_conversation: bool,
    enable_viz: bool,
) -> tuple[str, str, str, str]:
    """Execute the pipeline with the user's text and tool selections.

    Returns
    -------
    (json_output, rdf_output, graph_html, obsidian_md)
        Four strings for the four output tabs.
    """
    if not text or not text.strip():
        return (
            "⚠️ Please enter some text to analyze.",
            "",
            "<p style='color:#888'>No graph generated.</p>",
            "",
        )

    # Build the enabled-tools set from checkbox values
    enabled: Set[str] = set()
    if enable_linguistics:
        enabled.add("get_tags")
    if enable_triples:
        enabled.add("generate_triples")
    if enable_graph:
        enabled.add("generate_semantic_graph")
    if enable_obsidian:
        enabled.add("build_obsidian_note")
    if enable_conversation:
        enabled.add("analyze_conversation")
    if enable_viz:
        enabled.add("generate_viz")

    # Load config
    try:
        config.load_env()
    except RuntimeError:
        pass  # will fail inside run_pipeline if key missing

    # Build the prompt
    tool_descriptions = {
        "get_tags": "POS tagging, NER, and dependency parsing",
        "generate_triples": "RDF triple generation",
        "generate_semantic_graph": "interactive network visualization",
        "build_obsidian_note": "Obsidian markdown notes",
        "analyze_conversation": "conversation structure analysis",
        "generate_viz": "dependency tree SVG visualization",
    }

    enabled_desc = ", ".join(
        f"{name} ({tool_descriptions[name]})"
        for name in sorted(enabled)
    ) or "no tools selected"

    user_prompt = (
        f"Perform an ontological analysis on the following text using "
        f"only these tools: {enabled_desc}.\n\n"
        f"For each tool you call, provide the results in a structured JSON "
        f"response. If conversation analysis is requested and the text "
        f"contains speaker turns, also analyze the conversation structure.\n\n"
        f"Text to analyze:\n---\n{text.strip()}\n---\n\n"
        f"When finished, return a concise JSON summary."
    )

    # Run pipeline
    try:
        start = time.monotonic()
        result = run_pipeline(
            user_prompt=user_prompt,
            system_prompt=get_system_prompt(),
            max_iterations=30,
            enabled_tools=enabled,
        )
        elapsed = time.monotonic() - start
    except Exception as exc:
        tb = traceback.format_exc()
        return (
            f"❌ Pipeline error:\n\n```\n{tb}\n```",
            "",
            "<p style='color:#c00'>Graph generation failed.</p>",
            "",
        )

    # ── Gather output artifacts ───────────────────────────────────────

    # 1. JSON summary — the LLM's final response
    json_output = result
    if elapsed:
        json_output = (
            f"_Completed in {elapsed:.1f}s with tools: "
            f"{', '.join(sorted(enabled)) or 'none'}_\n\n{result}"
        )

    # 2. Turtle RDF — find the most recent .ttl file
    rdf_output = ""
    rdf_dir = config.rdf_dir
    if rdf_dir.exists():
        ttl_files = sorted(rdf_dir.glob("ontology_*.ttl"), reverse=True)
        if ttl_files:
            rdf_output = ttl_files[0].read_text(encoding="utf-8")

    # 3. Semantic graph HTML — render RDF via Talos visualizer
    graph_html = _format_graph_html(rdf_output)

    # 4. Obsidian notes — most recent .md
    obsidian_md = ""
    verse_dir = config.verse_dir
    if verse_dir.exists():
        md_files = sorted(verse_dir.glob("*.md"), reverse=True)
        if md_files and md_files[0].name != "Untitled.md":
            obsidian_md = md_files[0].read_text(encoding="utf-8")

    return json_output, rdf_output, graph_html, obsidian_md


def _format_graph_html(ttl_data: str) -> str:
    """Render TTL string to PyVis HTML and wrap in an iframe for Gradio."""
    if not ttl_data or not ttl_data.strip():
        return (
            "<div style='padding:20px;text-align:center;color:#666;'>"
            "No graph data available.</div>"
        )
    try:
        raw_html = render_rdf_graph(ttl_data, height="650px")
        return (
            f'<iframe id="graph-frame" srcdoc="{_html.escape(raw_html)}" '
            f'width="100%" height="650px" '
            f'style="border:none;border-radius:8px;"></iframe>'
        )
    except Exception as exc:
        return (
            f"<div style='color:red;padding:20px;'>"
            f"Error rendering graph: {_html.escape(str(exc))}</div>"
        )


def load_example(name: str) -> str:
    """Load a pre-defined example by name."""
    return EXAMPLES.get(name, "")


def _list_precomputed() -> list:
    """Scan assets/precomputed/ for existing folders."""
    from pathlib import Path
    base = Path(__file__).parent / "assets" / "precomputed"
    if not base.exists():
        print("[DEBUG] assets/precomputed/ does not exist")
        return []
    dirs = sorted([d.name for d in base.iterdir() if d.is_dir()])
    print(f"[DEBUG] _list_precomputed: found {len(dirs)} folders: {dirs}")
    return dirs


def _load_saved(folder_name: str):
    """Load a saved precomputed asset by folder name."""
    print(f"[DEBUG] _load_saved: folder={folder_name}")
    if not folder_name:
        print("[DEBUG] _load_saved: empty folder name, returning empty")
        return "", "", "", ""
    asset = load_precomputed_asset(folder_name)
    if asset:
        print(f"[DEBUG] _load_saved: loaded keys={list(asset.keys())}")
        return (
            json.dumps(asset["json"], indent=2),
            asset["ttl"],
            _format_graph_html(asset["ttl"]),
            asset["md"],
        )
    print(f"[DEBUG] _load_saved: no asset found for '{folder_name}'")
    return "", "", "", ""


def _save_precomputed(name: str, ttl: str, md: str, json_str: str) -> str:
    """Save current outputs to assets/precomputed/<name>/."""
    import os
    from pathlib import Path

    if not name.strip():
        return "⚠️ Please enter a save name."
    safe = name.strip().replace(" ", "_").lower()
    folder = Path(__file__).parent / "assets" / "precomputed" / safe
    folder.mkdir(parents=True, exist_ok=True)
    try:
        (folder / "graph.ttl").write_text(ttl, encoding="utf-8")
        html = render_rdf_graph(ttl, height="650px")
        (folder / "graph.html").write_text(html, encoding="utf-8")
        (folder / "note.md").write_text(md if md else "# No note generated.", encoding="utf-8")
        try:
            summary = json.loads(json_str.strip())
        except (json.JSONDecodeError, ValueError):
            # json_output may contain markdown or plain text, not valid JSON
            summary = {"raw_output": json_str.strip()[:2000]}
        (folder / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return f"✅ Saved to assets/precomputed/{safe}/"
    except Exception as exc:
        return f"❌ Save failed: {exc}"


def _on_example_change(name: str):
    """Handle dropdown change: load prompt text + pre-computed assets + case-aware SPARQL queries."""
    text = EXAMPLES.get(name, "")
    asset = load_precomputed_asset(name)

    # Case-aware SPARQL queries
    case_queries = get_queries_for_case(name)
    sparql_choices = list(case_queries.keys())
    sparql_default = sparql_choices[0] if sparql_choices else ""
    sparql_code = case_queries.get(sparql_default, "")

    if asset:
        return (
            text,
            json.dumps(asset["json"], indent=2),
            asset["ttl"],
            _format_graph_html(asset["ttl"]),
            asset["md"],
            gr.update(choices=sparql_choices, value=sparql_default),
            sparql_code,
        )
    return (
        text, "", "", "", "",
        gr.update(choices=sparql_choices, value=sparql_default),
        sparql_code,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Gradio UI
# ═══════════════════════════════════════════════════════════════════════════


UI_CSS = """
.app-container { max-width: 960px; margin: 0 auto; }
.output-box textarea { font-family: 'JetBrains Mono', 'Fira Code', monospace !important; font-size: 13px !important; }
footer { display: none !important; }
#title { text-align: center; margin-bottom: 0; }
#subtitle { text-align: center; color: #888; margin-top: 0; }
"""


def create_ui() -> gr.Blocks:
    """Build the Gradio interface with auth → dashboard → workspace routing."""

    from src.auth import register_user, authenticate_user, list_user_projects, create_project
    from src.config import resolve_project_dir

    with gr.Blocks(
        theme=gr.themes.Soft(),
        head="""<meta name="viewport" content="width=device-width, initial-scale=1.0">""",
        title="Talos — Ontological Deliberation Platform",
        css=UI_CSS,
    ) as app:

        # Session state
        user_state = gr.State(value=None)
        project_state = gr.State(value=None)

        # ═══════════════════════════════════════════════════════════════
        # STAGE 1: AUTHENTICATION
        # ═══════════════════════════════════════════════════════════════

        with gr.Column(visible=True, elem_id="auth-view") as auth_container:
            gr.Markdown("# 🏛️ Talos Platform — Portal")
            with gr.Tabs():
                with gr.Tab("Login"):
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login", variant="primary")
                    login_msg = gr.Markdown("")

                with gr.Tab("Register"):
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_btn = gr.Button("Create Account", variant="primary")
                    reg_msg = gr.Markdown("")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 2: PROJECT DASHBOARD
        # ═══════════════════════════════════════════════════════════════

        with gr.Column(visible=False, elem_id="dashboard-view") as project_container:
            user_header = gr.Markdown("# 📁 Select or Create a Project")
            with gr.Row():
                with gr.Column():
                    project_dropdown = gr.Dropdown(label="Your Projects", choices=[])
                    open_project_btn = gr.Button("Open Selected Project", variant="primary")
                with gr.Column():
                    new_proj_name = gr.Textbox(label="New Project Name", placeholder="e.g. student_council_2026")
                    create_proj_btn = gr.Button("Create New Project")
            dash_msg = gr.Markdown("")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 3: MAIN WORKSPACE (existing content)
        # ═══════════════════════════════════════════════════════════════

        with gr.Column(visible=False, elem_id="workspace-view") as workspace_container:
            active_proj_header = gr.Markdown("## 🔬 Active Workspace")

            # ── Chat widget (collapsed bar, expands on click) ───────────
        gr.HTML("""<style>
#chat-widget{position:fixed;bottom:0;right:20px;z-index:9998;font-family:-apple-system,BlinkMacSystemFont,sans-serif}
#chat-bar{cursor:pointer;background:#4a6cf7;color:#fff;padding:10px 18px;border-radius:12px 12px 0 0;font-size:14px;font-weight:600;user-select:none;display:flex;align-items:center;gap:8px;width:220px;justify-content:space-between}
#chat-bar:hover{background:#3651d5}
#chat-body{display:none;width:340px;height:420px;background:#fff;border:1px solid #e0e0e0;border-bottom:none;border-radius:12px 12px 0 0;box-shadow:0 -2px 16px rgba(0,0,0,.1);flex-direction:column}
#chat-body.open{display:flex}
#chat-header{background:#4a6cf7;color:#fff;padding:10px 14px;border-radius:12px 12px 0 0;display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:14px}
#chat-close{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;padding:0 4px}
#chat-messages{flex:1;overflow-y:auto;padding:12px;color:#333;font-size:13px}
#chat-input-row{display:flex;border-top:1px solid #e0e0e0;padding:8px}
#chat-input{flex:1;border:1px solid #ddd;border-radius:20px;padding:8px 14px;font-size:13px;outline:none}
#chat-send{margin-left:8px;background:#4a6cf7;color:#fff;border:none;border-radius:50%;width:36px;height:36px;cursor:pointer;font-size:16px}
</style>
<div id="chat-widget">
  <div id="chat-bar" onclick="
    var b=document.getElementById('chat-body');
    var bar=document.getElementById('chat-bar');
    b.classList.add('open');
    bar.style.display='none';
  ">💬 Chat <span style="font-size:11px;opacity:.7">▲</span></div>
  <div id="chat-body">
    <div id="chat-header">
      <span>💬 Ontology Assistant</span>
      <button id="chat-close" onclick="
        var b=document.getElementById('chat-body');
        var bar=document.getElementById('chat-bar');
        b.classList.remove('open');
        bar.style.display='flex';
      ">✕</button>
    </div>
    <div id="chat-messages"><div style="color:#888;text-align:center;margin-top:140px;font-size:13px">Ask me about the ontology graph...</div></div>
    <div id="chat-uploads" style="padding:4px 12px;font-size:11px;color:#888;min-height:20px"></div>
    <div id="chat-input-row">
      <input id="chat-file" type="file" style="display:none" onchange="addFile(this)">
      <button onclick="document.getElementById('chat-file').click()" style="background:none;border:none;font-size:18px;cursor:pointer;padding:4px" title="Upload file">📎</button>
      <input id="chat-input" type="text" placeholder="Type a message..." onkeypress="if(event.key==='Enter')sendMsg()">
      <button id="chat-send" onclick="sendMsg()">➤</button>
    </div>
  </div>
</div>
<script>
var chatPlaceholder=document.querySelector('#chat-messages div');
var chatFiles=[];
function addFile(input){
  var file=input.files[0];
  if(!file)return;
  chatFiles.push(file);
  var tag=document.createElement('span');
  tag.style.cssText='display:inline-block;background:#e8f0fe;color:#4a6cf7;padding:2px 8px;border-radius:10px;margin:2px;font-size:11px';
  tag.textContent='📄 '+file.name;
  document.getElementById('chat-uploads').appendChild(tag);
  input.value='';
}
function sendMsg(){
  var inp=document.getElementById('chat-input');
  var msg=inp.value.trim();
  if(!msg)return;
  if(chatPlaceholder)chatPlaceholder.style.display='none';
  var bubble=document.createElement('div');
  bubble.style.cssText='background:#4a6cf7;color:#fff;padding:8px 12px;border-radius:14px 14px 4px 14px;margin-bottom:8px;max-width:80%;align-self:flex-end;font-size:13px;word-wrap:break-word';
  bubble.textContent=msg;
  var wrap=document.createElement('div');
  wrap.style.cssText='display:flex;justify-content:flex-end';
  wrap.appendChild(bubble);
  document.getElementById('chat-messages').appendChild(wrap);
  document.getElementById('chat-messages').scrollTop=document.getElementById('chat-messages').scrollHeight;
  inp.value='';
}
</script>""")

        # ── Header ──────────────────────────────────────────────────
        gr.Markdown(
            """
            # 🔬 Ontological Discourse Analysis
            Map conversational text to structured ontologies — RDF triples,
            semantic networks, and Obsidian knowledge graphs.
            """,
            elem_id="title",
        )

        # ── Input Section ───────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                text_input = gr.Textbox(
                    label="Text to Analyze",
                    placeholder="Paste text or a conversation here...\n\nExample:\nAlice: Hello Professor!\nBob: Good morning, Alice.",
                    lines=8,
                    value=EXAMPLES[DEFAULT_EXAMPLE],
                )
            with gr.Column(scale=2):
                example_selector = gr.Dropdown(
                    label="📋 Load Example",
                    choices=list(EXAMPLES.keys()),
                    value=DEFAULT_EXAMPLE,
                )

        # ── Tool Selector ───────────────────────────────────────────
        gr.Markdown("### 🛠️ Select Tools to Activate")
        with gr.Row():
            with gr.Column(scale=1):
                enable_linguistics = gr.Checkbox(
                    value=True,
                    label=TOOL_UI_LABELS["get_tags"],
                    info="POS tags, NER, dependencies, noun chunks",
                )
                enable_triples = gr.Checkbox(
                    value=True,
                    label=TOOL_UI_LABELS["generate_triples"],
                    info="RDF triples (Turtle / JSON-LD)",
                )
                enable_conversation = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["analyze_conversation"],
                    info="Speakers, reply graphs, pragmatics",
                )
            with gr.Column(scale=1):
                enable_graph = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["generate_semantic_graph"],
                    info="Interactive pyvis HTML graph",
                )
                enable_obsidian = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["build_obsidian_note"],
                    info="Markdown notes with [[wikilinks]]",
                )
                enable_viz = gr.Checkbox(
                    value=False,
                    label=TOOL_UI_LABELS["generate_viz"],
                    info="displaCy SVG dependency tree",
                )

        # ── Run Button ──────────────────────────────────────────────
        with gr.Row():
            run_btn = gr.Button("🔍 Analyze", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear", size="lg")
        with gr.Row():
            saved_dropdown = gr.Dropdown(
                label="📂 Load Saved Graph",
                choices=_list_precomputed(),
                value=None,
                scale=2,
            )
        with gr.Row():
            save_name = gr.Textbox(
                label="Save Name",
                placeholder="e.g. case1_budget_debate",
                scale=2,
            )
            save_btn = gr.Button("💾 Save as Precomputed", variant="secondary", size="sm", scale=1)
        with gr.Row():
            file_upload = gr.File(
                label="📁 Upload Project Files",
                file_count="multiple",
                file_types=[".txt", ".md", ".ttl", ".json", ".pdf", ".csv"],
                scale=2,
            )
            upload_status = gr.Textbox(label="Upload Status", interactive=False, scale=1)

        # ── Status ──────────────────────────────────────────────────
        status = gr.Markdown("")

        # ── Output Tabs ─────────────────────────────────────────────
        with gr.Tabs():
            with gr.TabItem("📊 JSON Summary"):
                json_output = gr.Code(
                    label="Analysis Result",
                    language="json",
                    lines=20,
                    elem_classes="output-box",
                )

            with gr.TabItem("🐢 RDF Triples (Turtle)"):
                rdf_output = gr.Code(
                    label="RDF Serialization",
                    lines=20,
                    elem_classes="output-box",
                )

            with gr.TabItem("🕸️ Semantic Graph"):
                gr.HTML("""<style>
#graph-wrapper{position:relative}
#graph-frame{width:100%;height:650px;border:none;border-radius:8px}
#graph-frame.fs{position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:9999;border-radius:0;background:#fff}
#fs-btn{position:absolute;top:8px;right:8px;z-index:10;padding:6px 12px;background:#4a6cf7;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px}
#fs-btn:hover{background:#3651d5}
#fs-x{display:none;position:fixed;top:12px;right:12px;z-index:10001;width:36px;height:36px;background:#e74c3c;color:#fff;border:none;border-radius:50%;font-size:18px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)}
#fs-x:hover{background:#c0392b}
</style>
<div id="graph-wrapper">
<button id="fs-btn" onclick="
var f=document.getElementById('graph-frame');
var b=document.getElementById('fs-btn');
var x=document.getElementById('fs-x');
if(f.classList.contains('fs')){
f.classList.remove('fs');
b.style.display='';b.textContent='⛶ Full Screen';
x.style.display='none';
document.body.style.overflow='';
}else{
f.classList.add('fs');
b.textContent='⛶ Full Screen';b.style.display='none';
x.style.display='block';
document.body.style.overflow='hidden';
}
setTimeout(function(){f.contentWindow.postMessage('talos-fit','*')},300);
">⛶ Full Screen</button>
<button id="fs-x" onclick="
var f=document.getElementById('graph-frame');
var b=document.getElementById('fs-btn');
var x=document.getElementById('fs-x');
f.classList.remove('fs');
b.style.display='';b.textContent='⛶ Full Screen';
x.style.display='none';
document.body.style.overflow='';
setTimeout(function(){f.contentWindow.postMessage('talos-fit','*')},200);
" title="Exit">✕</button>
</div>
<script>
document.addEventListener('keydown',function(e){
if(e.key==='Escape'){
var f=document.getElementById('graph-frame');
if(f&&f.classList.contains('fs')){
var b=document.getElementById('fs-btn');
var x=document.getElementById('fs-x');
f.classList.remove('fs');
b.style.display='';b.textContent='⛶ Full Screen';
x.style.display='none';
document.body.style.overflow='';
setTimeout(function(){f.contentWindow.postMessage('talos-fit','*')},200);
}
}
});
</script>""")
                graph_output = gr.HTML(
                    label="Interactive Network",
                    value="<p style='color:#888;padding:2em;text-align:center'>"
                    "Enable <b>Semantic Network Visualizer</b> and run analysis "
                    "to see the graph here.</p>",
                )

            with gr.TabItem("📝 Obsidian Note"):
                obsidian_output = gr.Code(
                    label="Generated Markdown",
                    language="markdown",
                    lines=20,
                    elem_classes="output-box",
                )

            with gr.TabItem("🔍 SPARQL Queries"):
                with gr.Row():
                    preset_dropdown = gr.Dropdown(
                        label="Preset Query",
                        choices=list(PRESET_SPARQL_QUERIES.keys()),
                        value=list(PRESET_SPARQL_QUERIES.keys())[0],
                        scale=2,
                    )
                    run_query_btn = gr.Button("▶️ Execute Query", variant="primary", scale=1)
                sparql_editor = gr.Code(
                    label="SPARQL Query",
                    value=PRESET_SPARQL_QUERIES[list(PRESET_SPARQL_QUERIES.keys())[0]],
                    lines=12,
                )
                query_results = gr.Dataframe(
                    label="Query Results",
                    interactive=False,
                )

        # ── Event Handlers ──────────────────────────────────────────

        example_selector.change(
            fn=_on_example_change,
            inputs=[example_selector],
            outputs=[
                text_input, json_output, rdf_output, graph_output, obsidian_output,
                preset_dropdown, sparql_editor,
            ],
        )

        def _handle_upload(files, uid, pid):
            if not files:
                return "No files selected."
            if not uid or not pid:
                return "⚠️ Please open a project first."
            result = save_uploaded_files(files, uid, pid)
            if result["total_files"]:
                return f"✅ Uploaded {result['total_files']} file(s): {', '.join(result['saved_files'])}"
            return "⚠️ No supported files found."

        file_upload.upload(
            fn=_handle_upload,
            inputs=[file_upload, user_state, project_state],
            outputs=[upload_status],
        )

        saved_dropdown.change(
            fn=_load_saved,
            inputs=[saved_dropdown],
            outputs=[json_output, rdf_output, graph_output, obsidian_output],
        )

        run_btn.click(
            fn=lambda: "⏳ Running analysis...",
            outputs=[status],
        ).then(
            fn=run_analysis,
            inputs=[
                text_input,
                enable_linguistics,
                enable_triples,
                enable_graph,
                enable_obsidian,
                enable_conversation,
                enable_viz,
            ],
            outputs=[json_output, rdf_output, graph_output, obsidian_output],
        ).then(
            fn=lambda: "✅ Analysis complete.",
            outputs=[status],
        )

        # ── SPARQL handlers ──────────────────────────────────────────

        def _update_query(preset_name: str) -> str:
            return PRESET_SPARQL_QUERIES.get(preset_name, "")

        def _run_query(ttl_data: str, query_str: str):
            import pandas as pd
            df = execute_sparql(ttl_data, query_str)
            if df is None or df.empty:
                return pd.DataFrame({"Result": ["No matches found or query failed."]})
            return df

        preset_dropdown.change(
            fn=_update_query,
            inputs=[preset_dropdown],
            outputs=[sparql_editor],
        )

        run_query_btn.click(
            fn=_run_query,
            inputs=[rdf_output, sparql_editor],
            outputs=[query_results],
        )

        save_btn.click(
            fn=_save_precomputed,
            inputs=[save_name, rdf_output, obsidian_output, json_output],
            outputs=[status],
        )

        clear_btn.click(
            fn=lambda: ("", "", "", "", ""),
            outputs=[
                text_input,
                json_output,
                rdf_output,
                obsidian_output,
                status,
            ],
        )

        # ═══════════════════════════════════════════════════════════════
        # ROUTING LOGIC
        # ═══════════════════════════════════════════════════════════════

        def _handle_login(u, p):
            success, msg = authenticate_user(u, p)
            if success:
                projects = list_user_projects(u)
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    f"# 📁 Welcome back, **{u}**!",
                    gr.update(choices=projects, value=projects[0] if projects else None),
                    u,
                    f"✅ {msg}",
                )
            return (
                gr.update(visible=True), gr.update(visible=False),
                "", gr.update(), None,
                f"❌ {msg}",
            )

        login_btn.click(
            _handle_login,
            inputs=[login_user, login_pass],
            outputs=[auth_container, project_container, user_header,
                     project_dropdown, user_state, login_msg],
        )

        def _handle_register(u, p):
            success, msg = register_user(u, p)
            return f"{'✅' if success else '❌'} {msg}"

        reg_btn.click(
            _handle_register,
            inputs=[reg_user, reg_pass],
            outputs=[reg_msg],
        )

        def _handle_create_project(u, name):
            success, result = create_project(u, name)
            if success:
                projects = list_user_projects(u)
                return (
                    f"✅ Created project **{result}**",
                    gr.update(choices=projects, value=result),
                )
            return f"❌ {result}", gr.update()

        create_proj_btn.click(
            _handle_create_project,
            inputs=[user_state, new_proj_name],
            outputs=[dash_msg, project_dropdown],
        )

        def _handle_open_project(u, proj):
            if not u or not proj:
                return gr.update(visible=True), gr.update(visible=False), "", None
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                f"## 🔬 Active Project: **{proj}** (User: `{u}`)",
                proj,
            )

        open_project_btn.click(
            _handle_open_project,
            inputs=[user_state, project_dropdown],
            outputs=[project_container, workspace_container,
                     active_proj_header, project_state],
        )

    return app


# ═══════════════════════════════════════════════════════════════════════════
# HF Spaces requires the Blocks object at module level as `demo`
# ═══════════════════════════════════════════════════════════════════════════

demo = create_ui()
demo.queue()

# ═══════════════════════════════════════════════════════════════════════════
# Entry point (local dev)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
    )
