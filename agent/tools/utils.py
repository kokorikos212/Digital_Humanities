def generate_tool_metadata(name: str, model):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": model.__doc__,
            "parameters": model.model_json_schema(),
        },
    }