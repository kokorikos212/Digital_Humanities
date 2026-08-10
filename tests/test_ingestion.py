"""
Ingestion tests — file upload, path sandboxing, manifest updates.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.config import config, resolve_project_dir, resolve_documents_dir
from src.ingestion import save_uploaded_files


class TestIngestion:
    """Verify save_uploaded_files behaviour."""

    def test_saves_file_to_project_dir(self):
        """A .txt file lands in the correct documents/ folder."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Hello world")
            tmp = f.name

        try:
            result = save_uploaded_files([tmp], "test_user", "test_proj")
            assert result["status"] == "success"
            assert result["total_files"] == 1
            assert result["saved_files"][0].endswith(".txt")

            doc_dir = resolve_documents_dir("test_user", "test_proj")
            saved = doc_dir / Path(tmp).name
            assert saved.exists()
            assert saved.read_text() == "Hello world"
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_rejects_unsupported_extension(self):
        """Files with unsupported extensions are skipped."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            tmp = f.name

        try:
            result = save_uploaded_files([tmp], "test_user", "test_proj")
            assert result["total_files"] == 0
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_multiple_files(self):
        """Multiple supported files are all saved."""
        tmp_files = []
        for suffix in [".txt", ".md", ".json"]:
            f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            f.write(b"data")
            f.close()
            tmp_files.append(f.name)

        try:
            result = save_uploaded_files(tmp_files, "test_user", "test_proj")
            assert result["total_files"] == 3
        finally:
            for p in tmp_files:
                Path(p).unlink(missing_ok=True)

    def test_creates_manifest(self):
        """save_uploaded_files writes/updates a manifest.json."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("manifest test")
            tmp = f.name

        try:
            save_uploaded_files([tmp], "test_user", "test_proj")
            proj_dir = resolve_project_dir("test_user", "test_proj")
            manifest_path = proj_dir / "manifest.json"
            assert manifest_path.exists()

            manifest = json.loads(manifest_path.read_text())
            assert "documents" in manifest
            assert "last_updated" in manifest
            assert Path(tmp).name in manifest["documents"]
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_path_traversal_rejected(self):
        """Directory traversal filenames still resolve inside the project dir."""
        # save_uploaded_files uses Path(fname).name which strips directories
        # so ../../etc/passwd becomes just 'passwd'
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("traversal attempt")
            tmp = f.name

        # Simulate a malicious filename
        malicious = Path("/etc/passwd")
        try:
            result = save_uploaded_files([tmp], "test_user", "test_proj")
            # The saved file should be inside the documents dir, not at /etc/passwd
            doc_dir = resolve_documents_dir("test_user", "test_proj")
            saved = doc_dir / Path(tmp).name
            assert saved.exists()
            assert str(doc_dir) in str(saved.resolve())
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_project_dir_is_under_data_users(self):
        """Resolved project directory is always under data/users/."""
        proj = resolve_project_dir("alice", "debate_analysis")
        assert "data/users/alice/projects/debate_analysis" in str(proj)
        assert (proj / "documents").exists()
        assert (proj / "notes").exists()
        assert (proj / "graphs").exists()
