import os
from pydantic import BaseModel, Field, field_validator, ValidationError

from .utils import generate_tool_metadata

# 1. The "Schema Annotation" (Keep this for validation)
class WriteFileInput(BaseModel):
    """Save results to a markdown file."""
    filename: str = Field(..., description="The name of the file (e.g., 'report.md')")
    content: str = Field(..., description="The markdown content.")

    @field_validator('filename')
    @classmethod
    def validate_extension(cls, v: str) -> str:
        if not v.lower().endswith('.md'):
            raise ValueError("Constraint: Only .md files are permitted.")
        return v

# 2. The Tool Logic
class FolderRestrictedAgent:
    def __init__(self, folder_path: str = "output"):
        self.base_folder = os.path.abspath(folder_path)
        os.makedirs(self.base_folder, exist_ok=True)

    def _verify_path(self, requested_path: str) -> str:
        # Strip leading slashes to force relative joining
        requested_path = requested_path.lstrip(os.sep + (os.altsep or ""))
        target_path = os.path.abspath(os.path.join(self.base_folder, requested_path))
        if not target_path.startswith(self.base_folder):
            raise PermissionError("Path traversal attempt blocked.")
        return target_path


    def write_file(self, filename: str, content: str):
        try:
            valid_data = WriteFileInput(filename=filename, content=content)
            safe_path = self._verify_path(valid_data.filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(valid_data.content)
            
            # CRITICAL: Print to your terminal so you can see the REAL path
            print(f"\n[DEBUG] Writing file to: {safe_path}")
                
            return f"Successfully saved to {safe_path}"
        except Exception as e:
            print(f"\n[DEBUG] Failed to write: {str(e)}")
            return f"Tool Error: {str(e)}"

write_registry = [
    ("write_file", WriteFileInput)
]
write_tools = [generate_tool_metadata(n, m) for n, m in write_registry]