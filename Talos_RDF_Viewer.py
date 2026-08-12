# RDF TALOS Graph Viewer
# Christophe Roche : roche.university@gmail.com
# Version: 23/08/2025

import os
import tempfile
import webbrowser
import threading
import uuid
import html
import atexit
import shutil
from flask import Flask, request, render_template_string, session
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import OWL, DC, RDF, RDFS

# Namespaces
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OTV = Namespace("http://www.ontologia.fr/OTB/otv#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

# HTML templates (unchanged, but would be better as separate template files)
HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>RDF Graph Viewer</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F5F5F5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 500px;
            width: 90%;
            text-align: center;
        }
        h1 {
            color: #667eea;
            margin-bottom: 30px;
            font-size: 2.5rem;
            font-weight: 300;
        }
        .emoji { font-size: 3rem; margin-bottom: 20px; }
        p {
            color: #666;
            margin-bottom: 25px;
            font-size: 1.1rem;
            line-height: 1.5;
        }
        .file-upload {
            position: relative;
            display: inline-block;
            margin-bottom: 25px;
            width: 100%;
        }
        .file-input {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        .file-label {
            display: block;
            padding: 15px 25px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1rem;
            font-weight: 500;
        }
        .file-label:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102,126,234,0.4);
        }
        .submit-btn {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
        }
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(76,175,80,0.4);
        }
        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><strong>TALOS RDF Graph Viewer</strong></h1>
        <p><strong>TALOS-AI4SSH</strong> - <a href="https://talos-ai4ssh.uoc.gr/" target="_blank" rel="noopener">www.talos-ai4ssh.uoc.gr</a></p>
        <form method="post" action="/upload" enctype="multipart/form-data">
            <div class="file-upload">
                <input type="file" name="rdf_file" accept=".rdf,.xml,.ttl,.jsonld" required class="file-input" id="fileInput">
                <label for="fileInput" class="file-label" id="fileLabel">
                    📁 Select RDF File
                </label>
            </div>
            <input type="submit" value="📤 Upload and Analyze" class="submit-btn" id="submitBtn" disabled>
        </form>
    </div>
    
    <script>
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const label = document.getElementById('fileLabel');
            const submitBtn = document.getElementById('submitBtn');
            
            if (e.target.files.length > 0) {
                const fileName = e.target.files[0].name;
                label.textContent = '✅ ' + fileName;
                label.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
                submitBtn.disabled = false;
            } else {
                label.textContent = '📁 Select RDF File';
                label.style.background = 'linear-gradient(45deg, #667eea, #764ba2)';
                submitBtn.disabled = true;
            }
        });
    </script>
</body>
</html>
"""

UPLOAD_SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>File Uploaded</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F5F5F5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 600px;
            width: 90%;
            text-align: center;
        }
        h1 {
            color: #4CAF50;
            margin-bottom: 20px;
            font-size: 2rem;
            font-weight: 300;
        }
        .emoji { font-size: 3rem; margin-bottom: 20px; }
        p {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1rem;
            line-height: 1.5;
        }
        .btn {
            display: inline-block;
            padding: 12px 25px;
            margin: 10px;
            border: none;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            color: white;
            width: calc(100% - 20px);
        }
        .btn-info {
            background: linear-gradient(45deg, #FF9800, #F57C00);
        }
        .btn-primary {
            background: linear-gradient(45deg, #2196F3, #1976D2);
        }
        .btn-success {
            background: linear-gradient(45deg, #4CAF50, #45a049);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }
        input[type="submit"] {
            border: none;
            background: none;
            font: inherit;
            color: inherit;
            width: 100%;
        }
        .metadata-section {
            text-align: left;
            margin-top: 20px;
            background: #f8f9ff;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e0e4e7;
        }
        details {
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        summary {
            background: #f5f5f5;
            padding: 12px 15px;
            cursor: pointer;
            font-weight: 500;
            color: #333;
            transition: background 0.3s;
        }
        summary:hover {
            background: #e8e8e8;
        }
        .metadata-content {
            padding: 15px;
            background: white;
        }
        .metadata-item {
            margin: 8px 0;
            padding: 8px;
            background: #f9f9f9;
            border-radius: 4px;
            border-left: 3px solid #2196F3;
        }
        .metadata-label {
            font-weight: 600;
            color: #2196F3;
            display: block;
            margin-bottom: 4px;
        }
        .metadata-value {
            color: #555;
            word-break: break-word;
        }
        .namespace-item {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            background: #f5f5f5;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 3px solid #FF9800;
        }
        .namespace-prefix {
            font-weight: bold;
            color: #FF9800;
        }
        .namespace-uri {
            color: #666;
        }
        .namespace-uri a {
            color: #2196F3;
            text-decoration: none;
        }
        .namespace-uri a:hover {
            text-decoration: underline;
        }
        .stats-item {
            margin: 8px 0;
            padding: 8px;
            background: #f0f8ff;
            border-radius: 4px;
            border-left: 3px solid #4CAF50;
        }
        .stats-label {
            font-weight: 600;
            color: #4CAF50;
            display: inline-block;
            min-width: 150px;
        }
        .stats-value {
            color: #555;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">✅</div>
        <h1>File uploaded successfully!</h1>
        <p>Your RDF file has been analyzed. You can now choose properties to visualize, view the complete graph, or explore metadata.</p>
        
        <form method="get" action="/select" style="margin-bottom: 15px;">
            <input type="hidden" name="path" value="{{ path }}">
            <button type="submit" class="btn btn-primary">
                🎛️ Select Properties
            </button>
        </form>
        
        <form method="post" action="/view" style="margin-bottom: 15px;">
            <input type="hidden" name="rdf_path" value="{{ path }}">
            <input type="hidden" name="selected_props" value="__ALL__">
            <button type="submit" class="btn btn-success">
                🚀 View Graph
            </button>
        </form>
        
        <form method="get" action="/sparql" target="_blank" style="margin-bottom: 15px;">
            <input type="hidden" name="path" value="{{ path }}">
            <button type="submit" class="btn btn-primary">
                🔍 SPARQL Endpoint
            </button>
        </form>
        
        <button id="metadataBtn" class="btn btn-info" onclick="toggleMetadata()">
            📋 Show Metadata
        </button>
        
        <div id="metadataSection" class="metadata-section" style="display: none;">
            <details>
                <summary>📊 Graph Statistics</summary>
                <div class="metadata-content">
                    <div class="stats-item">
                        <span class="stats-label">Total triples:</span>
                        <span class="stats-value">{{ graph_stats.total_triples }}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Object properties:</span>
                        <span class="stats-value">{{ graph_stats.object_properties }}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Data properties:</span>
                        <span class="stats-value">{{ graph_stats.data_properties }}</span>
                    </div>
                    <div class="stats-item">
                        <span class="stats-label">Annotation properties:</span>
                        <span class="stats-value">{{ graph_stats.annotation_properties }}</span>
                    </div>
                </div>
            </details>
            
            {% if dublin_core_metadata %}
            <details>
                <summary>📖 Dublin Core Metadata ({{ dublin_core_metadata|length }} items)</summary>
                <div class="metadata-content">
                    {% for item in dublin_core_metadata %}
                    <div class="metadata-item">
                        <span class="metadata-label">{{ item.property }}</span>
                        <span class="metadata-value">{{ item.value }}</span>
                    </div>
                    {% endfor %}
                </div>
            </details>
            {% endif %}
            
            <details>
                <summary>🏷️ Declared Namespaces ({{ namespaces|length }} found)</summary>
                <div class="metadata-content">
                    {% for ns in namespaces %}
                    <div class="namespace-item">
                        <span class="namespace-prefix">{{ ns.prefix }}:</span>
                        <span class="namespace-uri"><a href="{{ ns.uri }}" target="_blank">{{ ns.uri }}</a></span>
                    </div>
                    {% endfor %}
                </div>
            </details>
        </div>
    </div>
    
    <script>
        function toggleMetadata() {
            const section = document.getElementById('metadataSection');
            const btn = document.getElementById('metadataBtn');
            
            if (section.style.display === 'none') {
                section.style.display = 'block';
                btn.textContent = '📋 Hide Metadata';
            } else {
                section.style.display = 'none';
                btn.textContent = '📋 Show Metadata';
            }
        }
    </script>
</body>
</html>
"""

SELECT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Property Selection</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F5F5F5;
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
        }
        h1 {
            color: #2196F3;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
            font-weight: 300;
        }
        .section {
            margin-bottom: 35px;
            background: #f8f9ff;
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #2196F3;
        }
        .section h2 {
            color: #1976D2;
            margin-bottom: 15px;
            font-size: 1.5rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .select-all {
            background: linear-gradient(45deg, #FF9800, #F57C00);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-left: auto;
        }
        .select-all:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255,152,0,0.3);
        }
        .property-item {
            display: flex;
            align-items: center;
            padding: 12px 15px;
            margin: 8px 0;
            background: white;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
            word-break: break-all;
        }
        .property-item:hover {
            background: #f0f7ff;
            border-color: #2196F3;
            transform: translateX(5px);
        }
        .property-checkbox {
            margin-right: 15px;
            transform: scale(1.2);
            accent-color: #2196F3;
        }
        .property-label {
            font-size: 0.95rem;
            color: #555;
            flex: 1;
        }
        .submit-container {
            text-align: center;
            margin-top: 40px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }
        .submit-btn {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(76,175,80,0.4);
        }
        .stats {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(45deg, #E8F5E8, #F1F8E9);
            border-radius: 15px;
            color: #2E7D32;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎛️ Property Selection</h1>
        
        <div class="stats">
            <strong>📊 Properties found:</strong>
            {{ object_properties|length }} objects • {{ data_properties|length }} data • {{ annotation_properties|length }} annotations
        </div>
        
        <form method="post" action="/view">
            <input type="hidden" name="rdf_path" value="{{ path }}">
            
            {% if object_properties %}
            <div class="section">
                <h2>
                    🔗 Object Properties ({{ object_properties|length }})
                    <button type="button" class="select-all" onclick="toggleCategory('object-prop', this)">Select All</button>
                </h2>
                {% for prop in object_properties %}
                <div class="property-item">
                    <input type="checkbox" class="property-checkbox object-prop" name="selected_props" value="{{ prop }}" id="obj_{{ loop.index }}">
                    <label class="property-label" for="obj_{{ loop.index }}">{{ prop }}</label>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if data_properties %}
            <div class="section">
                <h2>
                    📄 Data Properties ({{ data_properties|length }})
                    <button type="button" class="select-all" onclick="toggleCategory('data-prop', this)">Select All</button>
                </h2>
                {% for prop in data_properties %}
                <div class="property-item">
                    <input type="checkbox" class="property-checkbox data-prop" name="selected_props" value="{{ prop }}" id="data_{{ loop.index }}">
                    <label class="property-label" for="data_{{ loop.index }}">{{ prop }}</label>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if annotation_properties %}
            <div class="section">
                <h2>
                    💬 Annotation Properties ({{ annotation_properties|length }})
                    <button type="button" class="select-all" onclick="toggleCategory('anno-prop', this)">Select All</button>
                </h2>
                {% for prop in annotation_properties %}
                <div class="property-item">
                    <input type="checkbox" class="property-checkbox anno-prop" name="selected_props" value="{{ prop }}" id="anno_{{ loop.index }}">
                    <label class="property-label" for="anno_{{ loop.index }}">{{ prop }}</label>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="submit-container">
                <button type="submit" class="submit-btn">🚀 Generate Graph</button>
            </div>
        </form>
    </div>
    
    <script>
        function toggleCategory(categoryClass, button) {
            const checkboxes = document.querySelectorAll("." + categoryClass);
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            
            checkboxes.forEach(cb => cb.checked = !allChecked);
            
            button.textContent = allChecked ? 'Select All' : 'Deselect All';
            button.style.background = allChecked ? 
                'linear-gradient(45deg, #FF9800, #F57C00)' : 
                'linear-gradient(45deg, #f44336, #d32f2f)';
        }
        
        // Improve interaction with labels
        document.querySelectorAll('.property-item').forEach(item => {
            item.addEventListener('click', function(e) {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                }
            });
        });
    </script>
</body>
</html>
"""

# Create a dedicated temporary directory for our files
TEMP_DIR = tempfile.mkdtemp(prefix="rdf_viewer_")

# File mapping dictionary (in production, use a proper database)
file_mappings = {}

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for session management

def detect_format(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".rdf", ".xml"]:
        return "xml"
    elif ext == ".ttl":
        return "turtle"
    elif ext == ".jsonld":
        return "json-ld"
    else:
        return None

def extract_declared_namespaces(file_path):
    """Extrait uniquement les namespaces déclarés dans l'en-tête du fichier RDF/XML"""
    declared_namespaces = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            import re
            
            # Pattern amélioré pour capturer la balise rdf:RDF complète, même sur plusieurs lignes
            rdf_tag_pattern = r'<rdf:RDF[^>]*(?:\n[^>]*)*>'
            rdf_match = re.search(rdf_tag_pattern, content, re.MULTILINE | re.DOTALL)
            
            if rdf_match:
                rdf_tag = rdf_match.group(0)
                
                # Pattern pour extraire tous les attributs xmlns
                xmlns_pattern = r'xmlns(?::([^=\s]+))?\s*=\s*"([^"]+)"'
                xmlns_matches = re.findall(xmlns_pattern, rdf_tag)
                
                for prefix, uri in xmlns_matches:
                    # Si pas de préfixe spécifié, c'est le namespace par défaut
                    if not prefix:
                        prefix = "default"
                    
                    declared_namespaces.append({
                        'prefix': prefix,
                        'uri': uri
                    })
                
                # Trier par préfixe pour une meilleure lisibilité
                declared_namespaces.sort(key=lambda x: x['prefix'])
            else:
                # Fallback: si on ne trouve pas rdf:RDF, chercher dans tout le début du fichier
                xmlns_pattern = r'xmlns(?::([^=\s]+))?\s*=\s*"([^"]+)"'
                xmlns_matches = re.findall(xmlns_pattern, content[:2000])  # Première partie du fichier
                
                for prefix, uri in xmlns_matches:
                    if not prefix:
                        prefix = "default"
                    
                    declared_namespaces.append({
                        'prefix': prefix,
                        'uri': uri
                    })
                
                declared_namespaces.sort(key=lambda x: x['prefix'])
                
    except Exception as e:
        print(f"Erreur lors de l'extraction des namespaces: {e}")
        # En cas d'erreur, essayer une approche plus simple
        try:
            g = Graph()
            g.parse(file_path, format=detect_format(file_path))
            for prefix, namespace in g.namespaces():
                if prefix and prefix != '':
                    declared_namespaces.append({
                        'prefix': prefix,
                        'uri': str(namespace)
                    })
            declared_namespaces.sort(key=lambda x: x['prefix'])
        except:
            pass
    
    return declared_namespaces

def extract_ontology_dc_metadata(graph):
    """Extrait uniquement les métadonnées Dublin Core de la déclaration owl:Ontology"""
    dublin_core_metadata = []
    
    # Trouver l'URI de l'ontologie (ET SEULEMENT CELLE-CI)
    ontology_uri = None
    for s, p, o in graph:
        if p == RDF.type and o == OWL.Ontology:
            ontology_uri = s
            break
    
    if ontology_uri:
        # Rechercher uniquement les propriétés DC de cette ressource owl:Ontology
        for s, p, o in graph:
            if s == ontology_uri:  # SEULEMENT cette ressource owl:Ontology
                p_str = str(p)
                # Vérifier si c'est une propriété Dublin Core
                if "purl.org/dc/elements/1.1/" in p_str:
                    # Extraire le nom de la propriété
                    if p_str.endswith('/'):
                        prop_name = p_str.split('/')[-2]
                    else:
                        prop_name = p_str.split('/')[-1]
                    
                    dublin_core_metadata.append({
                        'property': f"dc:{prop_name}",
                        'value': str(o)
                    })
    
    # Trier les métadonnées par ordre alphabétique
    dublin_core_metadata.sort(key=lambda x: x['property'])
    
    return dublin_core_metadata

def extract_metadata_and_stats(graph, file_path):
    """Extract Dublin Core metadata, declared namespaces, and graph statistics"""
    
    # Extraire les métadonnées Dublin Core uniquement de owl:Ontology
    dublin_core_metadata = extract_ontology_dc_metadata(graph)
    
    # Extraire uniquement les namespaces déclarés dans l'en-tête
    declared_namespaces = extract_declared_namespaces(file_path)
    
    # Calculer les statistiques du graphe
    total_triples = len(graph)
    
    object_props, data_props, annotation_props = set(), set(), set()
    for s, p, o in graph:
        p_str = str(p)
        if isinstance(o, URIRef):
            object_props.add(p_str)
        elif "label" in p_str.lower() or "comment" in p_str.lower():
            annotation_props.add(p_str)
        else:
            data_props.add(p_str)
    
    graph_stats = {
        'total_triples': total_triples,
        'object_properties': len(object_props),
        'data_properties': len(data_props),
        'annotation_properties': len(annotation_props)
    }
    
    return dublin_core_metadata, declared_namespaces, graph_stats

# Cleanup function to remove temporary files on exit
def cleanup_temp_files():
    try:
        for file_token, file_path in list(file_mappings.items()):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Register cleanup function
atexit.register(cleanup_temp_files)

@app.route("/", methods=["GET"])
def home():
    return HOME_PAGE

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("rdf_file")
    if not file:
        return "No file uploaded", 400

    # Generate a unique token for this file
    file_token = str(uuid.uuid4())
    
    # Save file to our temporary directory
    filename = f"{file_token}{os.path.splitext(file.filename)[1]}"
    temp_file_path = os.path.join(TEMP_DIR, filename)
    file.save(temp_file_path)

    # Store the mapping
    file_mappings[file_token] = temp_file_path

    # Extract metadata and statistics for the upload success page
    try:
        fmt = detect_format(temp_file_path)
        if fmt:
            g = Graph()
            g.parse(temp_file_path, format=fmt)
            dublin_core_metadata, namespaces, graph_stats = extract_metadata_and_stats(g, temp_file_path)
        else:
            dublin_core_metadata, namespaces, graph_stats = [], [], {
                'total_triples': 0,
                'object_properties': 0,
                'data_properties': 0,
                'annotation_properties': 0
            }
    except Exception as e:
        print(f"Erreur lors de l'analyse du fichier: {e}")
        dublin_core_metadata, namespaces, graph_stats = [], [], {
            'total_triples': 0,
            'object_properties': 0,
            'data_properties': 0,
            'annotation_properties': 0
        }

    return render_template_string(
        UPLOAD_SUCCESS_PAGE, 
        path=file_token,  # Pass token instead of actual path
        dublin_core_metadata=dublin_core_metadata,
        namespaces=namespaces,
        graph_stats=graph_stats
    )

@app.route("/sparql", methods=["GET", "POST"])
def sparql_endpoint():
    file_token = request.args.get("path") or request.form.get("path")
    rdf_path = file_mappings.get(file_token)
    
    if not rdf_path or not os.path.exists(rdf_path):
        return "RDF file not found", 400

    fmt = detect_format(rdf_path)
    if not fmt:
        return "Unsupported file format", 400

    g = Graph()
    g.parse(rdf_path, format=fmt)

    query = request.form.get("query", "")
    results = []
    error_message = ""
    
    if request.method == "POST" and query:
        try:
            qres = g.query(query)
            
            # Get variable names from the first result
            if hasattr(qres, 'vars') and qres.vars:
                var_names = [str(var) for var in qres.vars]
            else:
                # Fallback: try to extract variable names from query
                import re
                select_match = re.search(r'SELECT\s+(.*?)\s+WHERE', query.upper())
                if select_match:
                    vars_str = select_match.group(1)
                    if vars_str.strip() == '*':
                        # For SELECT *, we need to infer from results
                        var_names = []
                        for row in qres:
                            var_names = [f"var{i}" for i in range(len(row))]
                            break
                    else:
                        var_names = [v.strip().replace('?', '') for v in vars_str.split()]
                else:
                    var_names = []
            
            for row in qres:
                result_dict = {}
                for i, value in enumerate(row):
                    var_name = var_names[i] if i < len(var_names) else f"var{i}"
                    result_dict[var_name] = str(value) if value else ""
                results.append(result_dict)
                
        except Exception as e:
            error_message = html.escape(str(e))

    # Escape user input to prevent XSS
    escaped_query = html.escape(query)
    escaped_error = html.escape(error_message) if error_message else ""

    sparql_page = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SPARQL Endpoint</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F5F5F5;
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
            font-weight: 300;
        }}
        .query-section {{
            margin-bottom: 30px;
            background: #f8f9ff;
            border-radius: 15px;
            padding: 20px;
            border-left: 5px solid #667eea;
        }}
        .query-label {{
            display: block;
            color: #667eea;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }}
        .query-textarea {{
            width: 100%;
            height: 200px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
            line-height: 1.4;
            resize: vertical;
            background: white;
        }}
        .query-textarea:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102,126,234,0.3);
        }}
        .button-group {{
            display: flex;
            gap: 15px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        .btn {{
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
        }}
        .btn-primary {{
            background: linear-gradient(45deg, #667eea, #764ba2);
        }}
        .btn-secondary {{
            background: linear-gradient(45deg, #95a5a6, #7f8c8d);
        }}
        .btn-info {{
            background: linear-gradient(45deg, #3498db, #2980b9);
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }}
        .results-section {{
            margin-top: 30px;
        }}
        .error {{
            background: #ffe6e6;
            color: #d63031;
            padding: 15px;
            border-radius: 8px;
            border-left: 5px solid #d63031;
            margin-bottom: 20px;
        }}
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .results-table th {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
        }}
        .results-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            word-break: break-word;
            max-width: 300px;
        }}
        .results-table tr:nth-child(even) {{
            background: #f8f9ff;
        }}
        .results-table tr:hover {{
            background: #e8f0fe;
        }}
        .no-results {{
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 20px;
        }}
        .examples {{
            margin-top: 20px;
            background: #f0f8ff;
            border-radius: 10px;
            padding: 15px;
            border-left: 5px solid #3498db;
        }}
        .examples h3 {{
            color: #3498db;
            margin-bottom: 10px;
        }}
        .example-query {{
            background: #fff;
            padding: 10px;
            margin: 8px 0;
            border-radius: 5px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            cursor: pointer;
            border: 1px solid #ddd;
            transition: all 0.3s;
        }}
        .example-query:hover {{
            border-color: #3498db;
            background: #f0f8ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 SPARQL Endpoint</h1>
        
        <form method="post">
            <input type="hidden" name="path" value="{file_token}">
            
            <div class="query-section">
                <label class="query-label" for="queryInput">SPARQL Query:</label>
                <textarea name="query" id="queryInput" class="query-textarea" placeholder="Enter your SPARQL query here...">{escaped_query}</textarea>
                
                <div class="button-group">
                    <button type="submit" class="btn btn-primary">▶️ Execute Query</button>
                    <button type="button" class="btn btn-secondary" onclick="clearQuery()">🗑️ Clear</button>
                    <button type="button" class="btn btn-info" onclick="toggleExamples()">💡 Examples</button>
                </div>
            </div>
        </form>
        
        <div class="examples" id="examples" style="display: none;">
            <h3>Example Queries:</h3>
            <div class="example-query" onclick="setQuery('SELECT * WHERE {{ ?s ?p ?o }} LIMIT 10')">
                SELECT * WHERE {{ ?s ?p ?o }} LIMIT 10
            </div>
            <div class="example-query" onclick="setQuery('SELECT DISTINCT ?type WHERE {{ ?s a ?type }}')">
                SELECT DISTINCT ?type WHERE {{ ?s a ?type }}
            </div>
            <div class="example-query" onclick="setQuery('SELECT ?s ?label WHERE {{ ?s rdfs:label ?label }} LIMIT 20')">
                SELECT ?s ?label WHERE {{ ?s rdfs:label ?label }} LIMIT 20
            </div>
            <div class="example-query" onclick="setQuery('CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s ?p ?o }} LIMIT 50')">
                CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s ?p ?o }} LIMIT 50
            </div>
        </div>
        

        {"" if not error_message else f'''
        <div class="results-section">
            <div class="error">
                <strong>Error:</strong> {escaped_error}
            </div>
        </div>
        '''}
        
    {"" if not results else f'''
    <div class="results-section">
        <h2 style="color: #667eea; margin-bottom: 15px;">📊 Query Results ({len(results)} rows)</h2>
        {(
            "<div class='no-results'>No results found</div>"
            if not results else
            "<table class='results-table'>"
            "<thead><tr>"
            + "".join(f"<th>{html.escape(var)}</th>" for var in results[0].keys())
            + "</tr></thead>"
            "<tbody>"
            + "".join(
                "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row.values()) + "</tr>"
                for row in results
            )
            + "</tbody></table>"
        )}
        </div>
        '''}
    </div>
    
    <script>
        function clearQuery() {{
            document.getElementById('queryInput').value = '';
        }}
        
        function toggleExamples() {{
            const examples = document.getElementById('examples');
            examples.style.display = examples.style.display === 'none' ? 'block' : 'none';
        }}
        
        function setQuery(query) {{
            document.getElementById('queryInput').value = query;
        }}
        
        // Add syntax highlighting-like behavior
        document.getElementById('queryInput').addEventListener('input', function(e) {{
            // Simple placeholder for future syntax highlighting
        }});
    </script>
</body>
</html>
"""

    return sparql_page

@app.route("/select", methods=["GET"])
def select():
    file_token = request.args.get("path")
    rdf_path = file_mappings.get(file_token)
    
    if not rdf_path or not os.path.exists(rdf_path):
        return "File not found", 400

    fmt = detect_format(rdf_path)
    if not fmt:
        return "Unsupported file format", 400

    g = Graph()
    g.parse(rdf_path, format=fmt)

    object_props, data_props, annotation_props = set(), set(), set()
    for s, p, o in g:
        p_str = str(p)
        if isinstance(o, URIRef):
            object_props.add(p_str)
        elif "label" in p_str.lower() or "comment" in p_str.lower():
            annotation_props.add(p_str)
        else:
            data_props.add(p_str)

    return render_template_string(
        SELECT_PAGE,
        path=file_token,  # Pass token instead of actual path
        object_properties=sorted(object_props),
        data_properties=sorted(data_props),
        annotation_properties=sorted(annotation_props)
    )

@app.route("/view", methods=["POST"])
def view_graph():
    file_token = request.form.get("rdf_path")
    rdf_path = file_mappings.get(file_token)
    selected_props = request.form.getlist("selected_props")

    if not rdf_path or not os.path.exists(rdf_path):
        return "RDF file not found", 400

    fmt = detect_format(rdf_path)
    if not fmt:
        return "Unsupported file format", 400

    g = Graph()
    g.parse(rdf_path, format=fmt)

    if "__ALL__" in selected_props:
        selected_props = [str(p) for p in g.predicates()]

    def truncate_label(label, max_length=35):
        """Tronque les labels trop longs : 15 premiers + ... + 15 derniers caractères"""
        if len(label) <= max_length:
            return label
        else:
            return label[:15] + "..." + label[-15:]

    def get_label(uri):
        """Gets the label of a URI using otv:shortConceptName in priority, then rdfs:label, then the URI"""
        if not isinstance(uri, URIRef):
            return truncate_label(str(uri))
        
        # 1. First look for otv:shortConceptName
        for short_name in g.objects(subject=uri, predicate=OTV.shortConceptName):
            return truncate_label(str(short_name))
        
        # 2. If no otv:shortConceptName, look for rdfs:label
        for label in g.objects(subject=uri, predicate=RDFS.label):
            return truncate_label(str(label))
        
        # 3. If no label, use the final part of the URI
        uri_str = str(uri)
        if "#" in uri_str:
            final_part = uri_str.split("#")[-1]
        elif "/" in uri_str:
            final_part = uri_str.split("/")[-1]
        else:
            final_part = uri_str
            
        return truncate_label(final_part)

    def get_tooltip(uri):
        """Gets the tooltip for a node with otv:conceptName and the URI"""
        if not isinstance(uri, URIRef):
            return str(uri)
        
        tooltip_parts = []
        
        # Add otv:conceptName if it exists
        for concept_name in g.objects(subject=uri, predicate=OTV.conceptName):
            tooltip_parts.append(f"conceptName: {str(concept_name)}")
        
        # Always add the URI
        tooltip_parts.append(f"URI: {str(uri)}")
        
        return "\n".join(tooltip_parts)

    # Analyser la structure du graphe pour identifier les types de nœuds
    all_subjects = set()
    all_objects = set()
    all_nodes = set()
    
    for s, p, o in g:
        if str(p) not in selected_props:
            continue
        
        if isinstance(s, URIRef):
            all_subjects.add(str(s))
            all_nodes.add(str(s))
        
        if isinstance(o, URIRef):
            all_objects.add(str(o))
            all_nodes.add(str(o))

    # Identifier les types de nœuds
    root_nodes = all_subjects - all_objects  # Nœuds qui sont sujets mais jamais objets
    terminal_nodes = all_objects - all_subjects  # Nœuds qui sont objets mais jamais sujets  
    intermediate_nodes = all_subjects & all_objects  # Nœuds qui sont à la fois sujets et objets

    # Import pyvis here to avoid import issues
    from pyvis.network import Network
    
    # Adapter la taille à la fenêtre
    net = Network(height="calc(100vh - 120px)", width="100%", directed=True, bgcolor="#ffffff", font_color="black")
    net.toggle_physics(True)

    # Couleurs pour les différents types de relations
    relation_colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", 
        "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
        "#F8C471", "#82E0AA", "#F1948A", "#85CDFF", "#FFB347"
    ]
    
    # Créer un mapping des relations vers les couleurs
    unique_relations = list(set(str(p) for s, p, o in g if str(p) in selected_props))
    relation_color_map = {}
    for i, relation in enumerate(unique_relations):
        relation_color_map[relation] = relation_colors[i % len(relation_colors)]

    for s, p, o in g:
        if str(p) not in selected_props:
            continue

        s_label = get_label(s) if isinstance(s, URIRef) else truncate_label(str(s))
        p_str = str(p)  # Convert to string first
        p_label = p_str.split("#")[-1] if "#" in p_str else (p_str.split("/")[-1] if "/" in p_str else p_str)

        s_tooltip = get_tooltip(s) if isinstance(s, URIRef) else str(s)
        p_tooltip = str(p)
        
        # Couleur des arêtes selon la relation
        edge_color = relation_color_map.get(str(p), "#808080")

        if isinstance(o, URIRef):
            o_label = get_label(o)
            o_tooltip = get_tooltip(o)
            
            # Couleurs des nœuds selon leur type (nouvelles couleurs)
            s_color = "#87CEEB" if str(s) in root_nodes else "#FFA07A" if str(s) in terminal_nodes else "#DFF2FF"
            o_color = "#87CEEB" if str(o) in root_nodes else "#FFA07A" if str(o) in terminal_nodes else "#DFF2FF"
            
            net.add_node(str(s), label=s_label, title=s_tooltip, shape="ellipse", color=s_color)
            net.add_node(str(o), label=o_label, title=o_tooltip, shape="ellipse", color=o_color)
            net.add_edge(str(s), str(o), label=p_label, title=p_tooltip, color=edge_color)
        else:
            lit_id = f"{s_label}_{p_label}_{str(o)}"
            o_label = truncate_label(str(o))
            
            s_color = "#87CEEB" if str(s) in root_nodes else "#FFA07A" if str(s) in terminal_nodes else "#DFF2FF"
            
            net.add_node(lit_id, label=o_label, title=str(o), shape="box", color="#E0E0E0")
            net.add_node(str(s), label=s_label, title=s_tooltip, shape="ellipse", color=s_color)
            net.add_edge(str(s), lit_id, label=p_label, title=p_tooltip, color=edge_color)

    output_path = os.path.join(tempfile.gettempdir(), "rdf_graph.html")
    net.write_html(output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Control panel HTML avec les nouvelles fonctionnalités Search et Reset améliorées
    control_panel_html = """
    <div style="padding: 10px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <input type="text" id="nodeSearch" placeholder="Search node (use * as wildcard)..." 
                   style="padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 200px; flex: 1; max-width: 300px;">
            <button onclick="searchNode()" 
                    style="padding: 6px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                Search
            </button>
            <button onclick="resetAll()" 
                    style="padding: 6px 12px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                Reset
            </button>
            <button id="freezeBtn" onclick="toggleFreeze()" 
                    style="padding: 6px 12px; background: #F5B027; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                Freeze (OFF)
            </button>
            <button onclick="deleteSelectedNode()" 
                    style="padding: 6px 12px; background: #F54927; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                Delete node
            </button>
        </div>
    </div>
    <style>
        button:hover { opacity: 0.8; transform: translateY(-1px); }
        #nodeSearch:focus { outline: none; border-color: #4CAF50; box-shadow: 0 0 5px rgba(76,175,80,0.3); }
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
        #mynetwork { height: calc(100vh - 120px) !important; width: 100% !important; }
    </style>
    <script>
        var isPhysicsEnabled = true;
        var isDragMode = false;
        
        function searchNode() {
            var pattern = document.getElementById('nodeSearch').value;
            if (!pattern) {
                alert("Please enter a search term");
                return;
            }
            
            var matches = [];
            var regex;
            
            try {
                // Convert wildcards * to regex .*
                var regexPattern = pattern.replace(/\*/g, '.*');
                regex = new RegExp(regexPattern, 'i'); // 'i' for case insensitive
            } catch (e) {
                alert("Invalid expression: " + e.message);
                return;
            }
            
            network.body.data.nodes.forEach(function(node) {
                if (regex.test(node.label) || regex.test(node.title)) {
                    matches.push(node.id);
                    // Mettre les nœuds en jaune ET en gras simultanément
                    network.body.data.nodes.update({
                        id: node.id, 
                        color: {background: 'yellow'},
                        font: {bold: true}
                    });
                }
            });
            
            if (matches.length > 0) {
                network.selectNodes(matches);
                network.fit({nodes: matches, animation: true});
                alert(matches.length + " node(s) found");
            } else {
                alert("No matching nodes found.");
            }
        }
        
        function resetAll() {
            // Effacer le champ de recherche
            document.getElementById('nodeSearch').value = '';
            
            // Forcer le rafraîchissement de la page
            window.location.reload();
        }
        
        function deleteSelectedNode() {
            var selectedNodes = network.getSelectedNodes();
            if (selectedNodes.length === 0) {
                alert("Please select a node to delete");
                return;
            }
            
            if (selectedNodes.length > 1) {
                alert("Please select only one node to delete");
                return;
            }
            
            var nodeId = selectedNodes[0];
            
            // Confirmation dialog
            if (confirm("Are you sure you want to delete this node and all its connections?")) {
                // Get all edges connected to this node
                var connectedEdges = network.getConnectedEdges(nodeId);
                
                // Remove all connected edges
                network.body.data.edges.remove(connectedEdges);
                
                // Remove the node
                network.body.data.nodes.remove(nodeId);
                
                // Update the network
                network.redraw();
            }
        }
        
        function toggleFreeze() {
            var btn = document.getElementById('freezeBtn');
            isPhysicsEnabled = !isPhysicsEnabled;
            
            if (isPhysicsEnabled) {
                // Turn physics ON (freeze OFF)
                network.setOptions({ 
                    physics: { 
                        enabled: true,
                        stabilization: { iterations: 100 }
                    }
                });
                btn.innerHTML = 'Freeze (OFF)';
                btn.style.background = '#F5B027';
                isDragMode = false;
                
                // Auto-recenter when turning physics ON
                setTimeout(function() {
                    network.fit({
                        animation: {
                            duration: 1000,
                            easingFunction: 'easeInOutQuad'
                        }
                    });
                }, 200);
                
            } else {
                // Turn physics OFF (freeze ON)
                network.setOptions({ 
                    physics: { enabled: false },
                    edges: { 
                        smooth: { 
                            enabled: true, 
                            type: 'straightCross',
                            forceDirection: 'none'
                        }
                    }
                });
                btn.innerHTML = 'Freeze (ON)';
                btn.style.background = '#F44336';
                isDragMode = true;
                
                // In freeze mode, don't auto-recenter when moving nodes
                network.off('dragEnd');
                network.off('dragging');
                
                // Only redraw without recentering
                network.on('dragEnd', function(params) {
                    if (isDragMode && params.nodes.length > 0) {
                        network.redraw();
                    }
                });
                
                network.on('dragging', function(params) {
                    if (isDragMode && params.nodes.length > 0) {
                        network.redraw();
                    }
                });
            }
        }
        
        // Allow search with Enter key
        document.getElementById('nodeSearch').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchNode();
            }
        });
        
        // Center the graph on loading
        network.once('stabilizationIterationsDone', function() {
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        });
        
        // Adapter la taille du réseau à la fenêtre
        window.addEventListener('resize', function() {
            if (network) {
                network.redraw();
                network.fit();
            }
        });
    </script>
    """

    # Insert panel right before the network div
    html_content = html_content.replace('<div id="mynetwork"', control_panel_html + '\n<div id="mynetwork"')

    return html_content

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(port=5000, debug=False)
