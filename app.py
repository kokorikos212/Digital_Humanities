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
from src.prompts import get_system_prompt, NAMED_PROMPTS
from src.tools import TOOL_UI_LABELS
from src.visualizer import render_rdf_graph
from src.queries import PRESET_SPARQL_QUERIES, execute_sparql, get_queries_for_case, compute_ttl_metadata
from src.precomputed import load_precomputed_asset
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
    enable_json: bool = True,
    enable_rdf: bool = True,
    enable_graph: bool = False,
    enable_obsidian: bool = False,
) -> tuple[str, str, str, str]:
    """Execute the pipeline. Only tab-checked outputs are generated.

    Returns
    -------
    (json_output, rdf_output, graph_html, obsidian_md)
    """
    if not text or not text.strip():
        return (
            "⚠️ Please enter some text to analyze.",
            "",
            "<p style='color:#888'>No graph generated.</p>",
            "",
        )

    # Build enabled-tools set from tab checkboxes (linguistics always on)
    enabled: set[str] = {"get_tags"}
    if enable_rdf:
        enabled.add("generate_triples")
    if enable_graph:
        enabled.add("generate_semantic_graph")
    if enable_obsidian:
        enabled.add("build_obsidian_note")

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

    deactivated = "<p style='color:#888;padding:2em;text-align:center'>Output deactivated by user.</p>"

    # 1. JSON summary
    json_output = deactivated if not enable_json else (
        f"_Completed in {elapsed:.1f}s with tools: "
        f"{', '.join(sorted(enabled)) or 'none'}_\n\n{result}"
    ) if elapsed else result

    # 2. Turtle RDF
    rdf_output = deactivated if not enable_rdf else ""
    if enable_rdf:
        rdf_dir = config.rdf_dir
        if rdf_dir.exists():
            ttl_files = sorted(rdf_dir.glob("ontology_*.ttl"), reverse=True)
            if ttl_files:
                rdf_output = ttl_files[0].read_text(encoding="utf-8")

    # 3. Semantic graph HTML
    graph_html = deactivated if not enable_graph else _format_graph_html(rdf_output)

    # 4. Obsidian notes
    obsidian_md = deactivated if not enable_obsidian else ""
    if enable_obsidian:
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
                upload_text_btn = gr.UploadButton(
                    "📂 Upload from Computer",
                    file_types=[".txt", ".md"],
                    size="sm",
                )
            with gr.Column(scale=2):
                example_selector = gr.Dropdown(
                    label="📋 Load Example",
                    choices=list(EXAMPLES.keys()),
                    value=DEFAULT_EXAMPLE,
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

        # ── API Keys Settings ────────────────────────────────────────
        with gr.Accordion("⚙️ API Keys & Settings", open=False):
            gr.Markdown("Manage personal API keys (saved in your user sandbox).")
            with gr.Row():
                user_ds_key = gr.Textbox(label="DeepSeek / LLM API Key", type="password", placeholder="sk-...")
                user_ocr_key = gr.Textbox(label="Bytez OCR API Key", type="password", placeholder="Bytez key...")
            with gr.Row():
                save_keys_btn = gr.Button("💾 Save Keys", variant="primary")
                clear_keys_btn = gr.Button("🗑️ Clear Keys")
            key_status = gr.Markdown("")

        # ── OCR Transcriber ──────────────────────────────────────────
        with gr.Accordion("📷 Image & Document OCR Transcriber", open=False):
            gr.Markdown("Extract or translate text from document photos & PDF scans.")
            with gr.Row():
                with gr.Column(scale=1):
                    ocr_file = gr.File(
                        label="Upload Image or PDF Scan",
                        file_types=[".png", ".jpg", ".jpeg", ".pdf", ".bmp"],
                    )
                    ocr_lang = gr.Dropdown(
                        label="Target Language",
                        choices=["Original", "Translate to English", "Translate to Greek"],
                        value="Original",
                    )
                    ocr_run_btn = gr.Button("⚡ Run OCR & Transcription", variant="primary")
                with gr.Column(scale=1):
                    ocr_output = gr.Textbox(
                        label="Extracted Transcript", lines=8, interactive=True,
                        placeholder="Transcribed text will appear here...",
                    )
                    with gr.Row():
                        ocr_push_btn = gr.Button("📥 Push to Main Input")
                        ocr_save_btn = gr.Button("💾 Save as Project Document (.md)")
                    ocr_status = gr.Markdown("")

        # ── Status ──────────────────────────────────────────────────
        status = gr.Markdown("")

        # ── Output tab checkboxes (always visible) ───────────────────
        with gr.Row():
            chk_json = gr.Checkbox(value=True, label="📊 JSON Summary")
            chk_rdf = gr.Checkbox(value=True, label="🐢 RDF Triples")
            chk_graph = gr.Checkbox(value=False, label="🕸️ Semantic Graph")
            chk_obsidian = gr.Checkbox(value=False, label="📝 Obsidian Note")

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

            with gr.TabItem("📊 Vocabulary Stats"):
                with gr.Tabs():
                    # --- Single-text analysis (feeds from main text input) ---
                    with gr.TabItem("📄 Single Text Analysis"):
                        gr.Markdown("Analyze the active text from the main input box.")
                        with gr.Row():
                            vocab_text = gr.Textbox(
                                label="Text to Analyze", lines=6,
                                placeholder="Paste text or use the main analysis box first...")
                            vocab_upload = gr.UploadButton("📂 Upload Text", file_types=[".txt", ".md"], size="sm")
                        vocab_run = gr.Button("🔬 Analyze Vocabulary", variant="primary")
                        vocab_metrics = gr.Markdown("")
                        vocab_table = gr.Dataframe(label="Top Discriminative Terms", interactive=False)

                    # --- Comparative analysis (two corpora) ---
                    with gr.TabItem("⚖️ Comparative Analysis"):
                        gr.Markdown("Compare two text corpora for divergence metrics.")
                        with gr.Row():
                            comp_text_a = gr.Textbox(label="Corpus A", lines=4,
                                placeholder="Paste corpus A...", scale=1)
                            comp_text_b = gr.Textbox(label="Corpus B", lines=4,
                                placeholder="Paste corpus B...", scale=1)
                        with gr.Row():
                            comp_upload_a = gr.UploadButton("📂 Upload A", file_types=[".txt", ".md"], size="sm")
                            comp_upload_b = gr.UploadButton("📂 Upload B", file_types=[".txt", ".md"], size="sm")
                        comp_run = gr.Button("🔬 Compute Divergence", variant="primary")
                        comp_metrics = gr.Markdown("")
                        comp_table = gr.Dataframe(label="Discriminative Terms (Z-Scores)", interactive=False)

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
                with gr.Accordion("📊 Graph Metadata", open=False):
                    metadata_btn = gr.Button("🔍 Analyze Active TTL", size="sm")
                    metadata_display = gr.Markdown("")

            with gr.TabItem("💻 Terminal & Files"):
                with gr.Row():
                    # Left: File Explorer
                    with gr.Column(scale=1):
                        gr.Markdown("### 📁 File Explorer")
                        file_path_status = gr.Markdown("📍 `/`")
                        file_tree_df = gr.Dataframe(
                            headers=["Name", "Type", "Size", "Relative Path"],
                            interactive=False,
                        )
                        refresh_files_btn = gr.Button("🔄 Refresh")
                        with gr.Accordion("📤 Upload Files", open=False):
                            upload_files = gr.File(
                                label="Select Files",
                                file_count="multiple",
                                file_types=[".txt", ".md", ".ttl", ".json", ".pdf", ".csv", ".py"],
                            )
                            upload_subfolder = gr.Textbox(
                                label="Target Subfolder", placeholder="documents", value="documents"
                            )
                            upload_btn = gr.Button("📤 Upload to Project", variant="primary")
                            upload_status_msg = gr.Markdown("")
                        with gr.Accordion("Delete Item", open=False):
                            delete_path = gr.Textbox(label="Relative Path to Delete")
                            delete_btn = gr.Button("🗑️ Delete", variant="stop")
                            delete_status = gr.Markdown("")
                        with gr.Accordion("Download File / Folder", open=False):
                            dl_path = gr.Textbox(label="Relative Path to Download")
                            dl_btn = gr.Button("📥 Prepare Download", variant="secondary")
                            dl_output = gr.File(label="Download", visible=True)

                    # Right: Text Terminal (single-shot bash with stateful cwd)
                    with gr.Column(scale=1):
                        gr.Markdown("### 💻 Bash Terminal")
                        terminal_output = gr.Code(label="Output", lines=10, interactive=False)
                        with gr.Row():
                            terminal_input = gr.Textbox(
                                label="Command", placeholder="e.g. ls -la, pwd, cat readme.md",
                                scale=3,
                            )
                            run_cmd_btn = gr.Button("▶️ Run", variant="primary", scale=1)
                        gr.Markdown("*Tip: use `cd` to navigate, all commands scoped to project*")
                        cwd_state = gr.State(value="")

        # ── Event Handlers ──────────────────────────────────────────

        def _load_file_to_text(file):
            if file is None:
                return ""
            try:
                content = Path(file.name).read_text(encoding="utf-8", errors="replace")
                return content
            except Exception as exc:
                return f"⚠️ Could not read file: {exc}"

        upload_text_btn.upload(
            fn=_load_file_to_text,
            inputs=[upload_text_btn],
            outputs=[text_input],
        )

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
            inputs=[text_input, chk_json, chk_rdf, chk_graph, chk_obsidian],
            outputs=[json_output, rdf_output, graph_output, obsidian_output],
        ).then(
            fn=lambda txt: txt,  # auto-fill vocab text
            inputs=[text_input],
            outputs=[vocab_text],
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

        def _show_metadata(ttl_data: str) -> str:
            if not ttl_data.strip():
                return "⚠️ No RDF data loaded."
            meta = compute_ttl_metadata(ttl_data)
            if "error" in meta:
                return f"❌ {meta['error']}"
            ns_md = "\n".join(
                f"- `{n['prefix']}:` <{n['uri']}>"
                for n in meta["namespaces"][:15]
            )
            return (
                f"### 📊 Graph Statistics\n"
                f"| Metric | Value |\n|--------|-------|\n"
                f"| Total Triples | **{meta['total_triples']}** |\n"
                f"| Object Properties | {meta['object_properties']} |\n"
                f"| Data Properties | {meta['data_properties']} |\n"
                f"| Annotation Properties | {meta['annotation_properties']} |\n\n"
                f"### 🏷️ Namespaces ({len(meta['namespaces'])})\n{ns_md}"
            )

        metadata_btn.click(
            fn=_show_metadata,
            inputs=[rdf_output],
            outputs=[metadata_display],
        )

        preset_dropdown.change(
            fn=_update_query,
            inputs=[preset_dropdown],
            outputs=[sparql_editor],
        )

        # ── Terminal & File Manager handlers ─────────────────────────

        import shutil as _shutil
        from src.tools.terminal import execute_project_bash
        from src.tools.file_manager import (
            list_project_directory, delete_project_item, prepare_download,
        )
        from src.config import resolve_project_dir

        def _handle_terminal(uid, pid, cmd, cwd):
            if not cmd.strip():
                return "", cwd, ""
            out, new_cwd = execute_project_bash(uid, pid, cmd, cwd)
            return f"$ {cmd}\n{out}\n", new_cwd, ""

        run_cmd_btn.click(
            fn=_handle_terminal,
            inputs=[user_state, project_state, terminal_input, cwd_state],
            outputs=[terminal_output, cwd_state, terminal_input],
        )

        terminal_input.submit(
            fn=_handle_terminal,
            inputs=[user_state, project_state, terminal_input, cwd_state],
            outputs=[terminal_output, cwd_state, terminal_input],
        )

        def _handle_list_files(uid, pid, cwd):
            df = list_project_directory(uid, pid, cwd)
            path_label = f"📍 `/{cwd or ''}`"
            return df, path_label

        def _handle_delete(uid, pid, rel):
            if not rel.strip():
                return "⚠️ Enter a relative path to delete."
            return delete_project_item(uid, pid, rel)

        def _handle_download(uid, pid, rel):
            if not rel.strip():
                return None
            result = prepare_download(uid, pid, rel)
            if result.startswith("Error:"):
                print(f"[DEBUG] Download error: {result}")
                return None
            return result

        refresh_files_btn.click(
            fn=_handle_list_files,
            inputs=[user_state, project_state, cwd_state],
            outputs=[file_tree_df, file_path_status],
        )

        delete_btn.click(
            fn=_handle_delete,
            inputs=[user_state, project_state, delete_path],
            outputs=[delete_status],
        )

        def _handle_project_upload(files, uid, pid, subfolder):
            if not files:
                return "No files selected."
            if not uid or not pid:
                return "⚠️ Open a project first."
            proj = resolve_project_dir(uid, pid)
            target = (proj / (subfolder.strip() or "documents")).resolve()
            if not str(target).startswith(str(proj)):
                return "⚠️ Invalid subfolder path."
            target.mkdir(parents=True, exist_ok=True)
            saved = []
            for f in files:
                fname = _shutil.copy(str(f.name), str(target / f.name.split("/")[-1]))
                saved.append(f.name.split("/")[-1])
            return f"✅ Uploaded {len(saved)} file(s): {', '.join(saved)}"

        upload_btn.click(
            fn=_handle_project_upload,
            inputs=[upload_files, user_state, project_state, upload_subfolder],
            outputs=[upload_status_msg],
        )

        dl_btn.click(
            fn=_handle_download,
            inputs=[user_state, project_state, dl_path],
            outputs=[dl_output],
        )

        # ── Vocabulary Stats handlers ──────────────────────────────────

        def _vocab_upload(file):
            if file is None:
                return ""
            return Path(file.name).read_text(encoding="utf-8", errors="replace")

        def _single_vocab(text):
            import pandas as _pd
            from src.tools.statistics import compute_log_odds_ratio
            if not text.strip():
                return "⚠️ No text to analyze.", _pd.DataFrame()
            # Compare first half vs second half as proxy for discriminative
            words = text.split()
            mid = len(words) // 2
            ta, tb = " ".join(words[:mid]), " ".join(words[mid:])
            if len(ta) < 20 or len(tb) < 20:
                ta, tb = text[:len(text)//2], text[len(text)//2:]
            df = compute_log_odds_ratio(ta, tb, top_n=15)
            return f"**{len(words)} words, {df.shape[0]} discriminative terms**", df

        def _comp_vocab(ta, tb):
            import pandas as _pd
            from src.tools.statistics import compute_corpus_divergence, compute_log_odds_ratio
            if not ta.strip() or not tb.strip():
                return "⚠️ Paste text for both corpora.", _pd.DataFrame()
            div = compute_corpus_divergence(ta, tb)
            df = compute_log_odds_ratio(ta, tb, top_n=15)
            sig = "✅ Significant" if div["statistically_significant"] else "⚠️ Not significant"
            md = (
                f"| Metric | Value |\n|--------|-------|\n"
                f"| Jensen-Shannon Divergence | **{div['jsd']}** |\n"
                f"| χ² p-value | **{div['chi2_p_value']}** ({sig}) |\n"
                f"| Cosine Similarity | **{div['cosine_similarity']}** |\n"
            )
            return md, df

        vocab_upload.upload(fn=_vocab_upload, inputs=[vocab_upload], outputs=[vocab_text])
        comp_upload_a.upload(fn=_vocab_upload, inputs=[comp_upload_a], outputs=[comp_text_a])
        comp_upload_b.upload(fn=_vocab_upload, inputs=[comp_upload_b], outputs=[comp_text_b])

        vocab_run.click(fn=_single_vocab, inputs=[vocab_text], outputs=[vocab_metrics, vocab_table])
        comp_run.click(fn=_comp_vocab, inputs=[comp_text_a, comp_text_b], outputs=[comp_metrics, comp_table])

        # ── API Keys handlers ───────────────────────────────────────
        from src.auth_keys import save_user_keys, resolve_api_key, mask_key

        def _handle_save_keys(uid, ds, ocr):
            msg = save_user_keys(uid, {"DEEPSEEK_KEY": ds, "BYTEZ_API_KEY": ocr})
            return msg, mask_key(resolve_api_key(uid, "DEEPSEEK_KEY")), mask_key(resolve_api_key(uid, "BYTEZ_API_KEY"))

        def _handle_clear_keys(uid):
            save_user_keys(uid, {"DEEPSEEK_KEY": "", "BYTEZ_API_KEY": ""})
            return "✅ Keys cleared.", "", ""

        save_keys_btn.click(
            fn=_handle_save_keys,
            inputs=[user_state, user_ds_key, user_ocr_key],
            outputs=[key_status, user_ds_key, user_ocr_key],
        )
        clear_keys_btn.click(
            fn=_handle_clear_keys,
            inputs=[user_state],
            outputs=[key_status, user_ds_key, user_ocr_key],
        )

        # ── OCR handlers ────────────────────────────────────────────
        def _handle_ocr(file_obj, lang):
            if file_obj is None:
                return "Please upload an image or PDF scan."
            from src.tools.transcription import transcribe_document_image
            return transcribe_document_image(file_obj.name, target_language=lang)

        def _handle_ocr_save(uid, pid, file_obj, text):
            if not file_obj or not text.strip():
                return "No transcript to save."
            from src.ingestion import save_transcribed_document
            return save_transcribed_document(uid, pid, file_obj.name, text)

        ocr_run_btn.click(fn=_handle_ocr, inputs=[ocr_file, ocr_lang], outputs=[ocr_output])
        ocr_push_btn.click(fn=lambda t: t, inputs=[ocr_output], outputs=[text_input])
        ocr_save_btn.click(
            fn=_handle_ocr_save,
            inputs=[user_state, project_state, ocr_file, ocr_output],
            outputs=[ocr_status],
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
                    gr.update(visible=False),    # auth
                    gr.update(visible=True),     # dashboard
                    gr.update(visible=False),    # workspace stays hidden
                    f"# 📁 Welcome back, **{u}**!",
                    gr.update(choices=projects, value=projects[0] if projects else None),
                    u,
                    f"✅ {msg}",
                )
            return (
                gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
                "", gr.update(), None,
                f"❌ {msg}",
            )

        login_btn.click(
            _handle_login,
            inputs=[login_user, login_pass],
            outputs=[auth_container, project_container, workspace_container,
                     user_header, project_dropdown, user_state, login_msg],
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
                return (gr.update(visible=True), gr.update(visible=False),
                        "", None, "", "", "")
            from src.config import resolve_project_dir
            from src.precomputed import load_project_artifacts
            p_dir = resolve_project_dir(u, proj)
            ttl, html, md = load_project_artifacts(p_dir)
            graph_html = _format_graph_html(ttl) if ttl else (
                "<p style='color:#888;padding:2em;text-align:center'>"
                "No graph generated yet for this project.</p>"
            )
            return (
                gr.update(visible=False),     # dashboard
                gr.update(visible=True),      # workspace
                f"## 🔬 Active Project: **{proj}** (User: `{u}`)",
                proj,
                ttl,                          # RDF output
                graph_html,                   # Graph HTML
                md if md else "# No notes yet.",
            )

        open_project_btn.click(
            _handle_open_project,
            inputs=[user_state, project_dropdown],
            outputs=[project_container, workspace_container,
                     active_proj_header, project_state,
                     rdf_output, graph_output, obsidian_output],
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
