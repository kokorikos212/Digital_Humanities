from .toolset import linguisticTools, LinguisticInput
from .tools_to_write import FolderRestrictedAgent, WriteFileInput

# 1. THE LLM INTERFACE (JSON Schemas)
# We use Pydantic's model_json_schema to generate these on the fly.
all_tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "get_linguistic_annotations",
            "description": LinguisticInput.__doc__,
            "parameters": LinguisticInput.model_json_schema()
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
# We export the classes directly so agent.py can instantiate them.
tool_handlers = {
    "linguistic": linguisticTools,
    "writer": FolderRestrictedAgent
}