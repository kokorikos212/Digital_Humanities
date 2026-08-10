"""
File manager tests — directory listing and safe deletion.
"""

import shutil
from pathlib import Path

from src.config import resolve_project_dir, config
from src.tools.file_manager import list_project_directory, delete_project_item


class TestFileManager:
    """Verify file manager listing and deletion."""

    def test_list_empty_project_has_documents_folder(self):
        """A new project shows documents/ in the listing."""
        proj = resolve_project_dir("fm_user", "fm_proj")
        (proj / "documents" / "sample.txt").write_text("hello")
        df = list_project_directory("fm_user", "fm_proj", "")
        assert "documents" in df["Name"].values
        shutil.rmtree(config.project_root / "data" / "users" / "fm_user", ignore_errors=True)

    def test_delete_file(self):
        """Deleting a file returns success and removes it."""
        proj = resolve_project_dir("fm_user", "fm_proj")
        (proj / "test_delete.txt").write_text("bye")
        result = delete_project_item("fm_user", "fm_proj", "test_delete.txt")
        assert "Deleted" in result
        assert not (proj / "test_delete.txt").exists()
        shutil.rmtree(config.project_root / "data" / "users" / "fm_user", ignore_errors=True)

    def test_delete_nonexistent(self):
        """Deleting a non-existent path returns error."""
        result = delete_project_item("fm_user", "fm_proj", "ghost.txt")
        assert "does not exist" in result
        shutil.rmtree(config.project_root / "data" / "users" / "fm_user", ignore_errors=True)

    def test_delete_outside_sandbox_blocked(self):
        """Attempting to delete outside project root is blocked."""
        result = delete_project_item("fm_user", "fm_proj", "../../../etc/passwd")
        assert "Cannot delete" in result
        shutil.rmtree(config.project_root / "data" / "users" / "fm_user", ignore_errors=True)
