import json
import spacy
from pydantic import BaseModel, Field
from typing import Type, List
from spacy import displacy
from pathlib import Path
from typing import Literal

from .utils import generate_tool_metadata


class LinguisticInput(BaseModel):
    """Analyze text for POS, dependencies, or entities with professional visualization."""
    text: str = Field(..., description="The sentence to be analyzed.")
    visualize: bool = Field(False, description="Whether to generate a visualization.")
    style: Literal["dep", "ent"] = Field(
        "dep", 
        description="The style of visualization: 'dep' for syntax trees, 'ent' for named entities."
    )

# 2. The Container Class
# 2. The Updated Toolkit Class
class linguisticTools:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.viz_options = {
            "dep": {"compact": False, "color": "#F0F0F0", "bg": "#2C3E50", "font": "Verdana"},
            "ent": {"colors": {"ORG": "#7aecec", "PRODUCT": "#bfe1d9"}} # Custom colors for entities
        }

    def get_linguistic_annotations(self, text: str, visualize: bool = False, style: str = "dep"):
        doc = self.nlp(text)
        
        # 1. Prepare Data Output
        results = {
            "tokens": [{"text": t.text, "pos": t.pos_} for t in doc],
            "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
        }

        # 2. Handle Visualization (Entity vs Dependency)
        if visualize:
            # We use displacy.render (non-blocking) instead of .serve
            options = self.viz_options.get(style, {})
            svg = displacy.render(doc, style=style, options=options, jupyter=False)
            
            file_name = f"viz_{style}.svg"
            Path(file_name).write_text(svg, encoding="utf-8")
            results["visualization_saved"] = file_name
            results["view_type"] = "Named Entity Recognition" if style == "ent" else "Dependency Parse"

        return results

    @staticmethod
    def generate_tool_metadata(name: str, model: Type[BaseModel]) -> dict:
        """Helper to convert Pydantic models to the Tool Dictionary format."""
        schema = model.model_json_schema()
        schema.pop("title", None)
        if "properties" in schema:
            for prop in schema["properties"].values():
                prop.pop("title", None)
        
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": model.__doc__,
                "parameters": schema,
            },
        }


# 3. Scaling: The Registry
# To add more functions, just add the model and name to this list
linguistic_registry = [
    ("get_linguistic_annotations", LinguisticInput)
]

linguistic_tools = [generate_tool_metadata(n, m) for n, m in linguistic_registry]