"""
File writer tool — safe markdown file output restricted to a single directory.

Uses path-traversal protection to ensure all writes stay within the
configured output directory.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

from src.config import config
from src.visualizer import render_rdf_graph


# ── Input schema ──────────────────────────────────────────────────────────


class WriteFileInput(BaseModel):
    """Save results to a markdown file."""

    filename: str = Field(..., description="The name of the file (e.g., 'report.md')")
    content: str = Field(..., description="The markdown content.")

    @field_validator("filename")
    @classmethod
    def validate_extension(cls, v: str) -> str:
        if not v.lower().endswith(".md"):
            raise ValueError("Constraint: Only .md files are permitted.")
        return v


# ── Tool implementation ───────────────────────────────────────────────────


class FolderRestrictedAgent:
    """Safe file writer restricted to the project output directory."""

    def __init__(self):
        config.ensure_output_dirs()
        self.base_folder = str(config.output_dir.resolve())

    def _verify_path(self, requested_path: str) -> str:
        """Prevent path-traversal attacks."""
        requested_path = requested_path.lstrip(os.sep + (os.altsep or ""))
        target_path = os.path.abspath(os.path.join(self.base_folder, requested_path))
        if not target_path.startswith(self.base_folder):
            raise PermissionError("Path traversal attempt blocked.")
        return target_path

    def write_file(self, filename: str, content: str) -> str:
        """Write *content* to *filename* under the output directory."""
        try:
            valid_data = WriteFileInput(filename=filename, content=content)
            safe_path = self._verify_path(valid_data.filename)

            os.makedirs(os.path.dirname(safe_path), exist_ok=True)

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(valid_data.content)

            return f"Successfully saved to {safe_path}"
        except Exception as e:
            return f"Tool Error: {str(e)}"

    def export_graph_html(self, ttl_data: str, base_name: str = "graph") -> str:
        """Render *ttl_data* to an interactive PyVis HTML file.

        Parameters
        ----------
        ttl_data:
            Turtle/RDF string to render.
        base_name:
            Base filename without extension (default: ``"graph"``).

        Returns
        -------
        A status message with the saved file path, or an error string.
        """
        if not ttl_data or not ttl_data.strip():
            return "Tool Error: No RDF data provided for graph export."
        try:
            html_content = render_rdf_graph(ttl_data, height="650px")
            safe_name = f"{base_name}.html"
            safe_path = self._verify_path(safe_name)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return f"Graph exported to {safe_path}"
        except Exception as e:
            return f"Tool Error: Graph export failed: {str(e)}"


# ── Registry helpers ──────────────────────────────────────────────────────

write_registry = [
    ("write_file", WriteFileInput),
]
