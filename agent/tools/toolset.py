from pydantic import BaseModel, Field
from typing import Literal
from typing import Type, List
from pathlib import Path
import spacy
import os
import time

# Ensure these names match the ones in __init__.py
class AnalysisInput(BaseModel):
    """Input for basic linguistic analysis."""
    text: str = Field(..., description="The sentence to be analyzed for POS and entities.")

class VisualizationInput(BaseModel):
    """Input for creating a visual representation of text."""
    text: str = Field(..., description="The sentence to visualize.")
    style: Literal["dep", "ent"] = Field(
        "dep", 
        description="Style: 'dep' for syntax trees, 'ent' for entities."
    )

class linguisticTools:
    def __init__(self, output_dir="visualizations"):
        # Load spacy once during initialization
        self.nlp = spacy.load("en_core_web_sm")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_tags(self, text: str):
        """Method for the 'analyze_text' tool."""
        doc = self.nlp(text)
        return {
            "tokens": [t.text for t in doc],
            "pos": [t.pos_ for t in doc],
            "entities": [(ent.text, ent.label_) for ent in doc.ents]
        }

    def generate_viz(self, text: str, style: str = "dep"):
        """Method for the 'visualize_text' tool."""
        doc = self.nlp(text)
        svg = spacy.displacy.render(doc, style=style, page=False)
        filename = f"viz_{style}_{int(time.time())}.svg"
        full_path = os.path.join(self.output_dir, filename)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(svg)
        return {"status": "success", "saved_at": full_path}
    
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
    ("get_tags", AnalysisInput),
    ("generate_viz", VisualizationInput)
]

linguistic_tools = [linguisticTools.generate_tool_metadata(n, m) for n, m in linguistic_registry]