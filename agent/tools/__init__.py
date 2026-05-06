from .toolset import (
    linguisticTools, 
    AnalysisInput, 
    VisualizationInput
)

from .tools_to_write import (
    FolderRestrictedAgent, 
    WriteFileInput
)

# 1. THE LLM INTERFACE (JSON Schemas)
# Split into three distinct capabilities: Analysis, Visualization, and File Writing.
all_tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "get_tags",
            "description": "Extract tokens, POS tags, and named entities from text. Use this for general linguistic questions.",
            "parameters": AnalysisInput.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_viz", # Ensure this matches tool_map
            "description": "Create an SVG visualization. ALWAYS use this name 'generate_viz' for visualizations.",
            "parameters": VisualizationInput.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": WriteFileInput.__doc__,
            "parameters": WriteFileInput.model_json_schema()
        }
    }
]

# 2. THE EXECUTION INTERFACE (Logic)
# Mapping keys to the Classes for instantiation in agent.py
tool_handlers = {
    "linguistic": linguisticTools,
    "writer": FolderRestrictedAgent
}