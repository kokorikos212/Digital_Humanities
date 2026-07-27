"""
Tests for centralized configuration (src/config.py).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.config import Config


class TestConfig:
    """Verify Config dataclass behaviour."""

    def test_project_root_resolves_to_repo_root(self):
        """Config.project_root should point to the repo root directory."""
        cfg = Config()
        root = cfg.project_root
        assert root.is_dir()
        # The repo root should contain run_pipeline.py
        assert (root / "run_pipeline.py").exists()

    def test_output_dir_is_under_project_root(self):
        """output_dir should be a subdirectory of project_root."""
        cfg = Config()
        assert cfg.output_dir == cfg.project_root / "output"

    def test_property_paths_are_absolute(self):
        """All path properties should be absolute Paths."""
        cfg = Config()
        for attr in [
            "output_dir",
            "data_dir",
            "graphs_dir",
            "rdf_dir",
            "conversations_dir",
            "verse_dir",
        ]:
            p = getattr(cfg, attr)
            assert isinstance(p, Path), f"{attr} is not a Path"
            assert p.is_absolute(), f"{attr} is not absolute"

    def test_default_values(self):
        """Sanity-check default settings."""
        cfg = Config()
        assert cfg.model == "deepseek-chat"
        assert cfg.max_iterations == 30
        assert cfg.spacy_model == "en_core_web_sm"
        assert cfg.deepseek_key == ""

    def test_ensure_output_dirs_creates_directories(self):
        """ensure_output_dirs should create all output subdirectories."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(project_root=Path(tmp))
            cfg.ensure_output_dirs()

            for d in [
                cfg.output_dir,
                cfg.graphs_dir,
                cfg.rdf_dir,
                cfg.conversations_dir,
                cfg.verse_dir,
            ]:
                assert d.exists(), f"{d} was not created"
                assert d.is_dir(), f"{d} is not a directory"

    def test_load_env_reads_key(self):
        """load_env should extract DEEPSEEK_KEY from a .env file."""
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("DEEPSEEK_KEY=sk-test-key-12345\n")

            cfg = Config(project_root=Path(tmp))
            cfg.load_env(env_file=env_file)
            assert cfg.deepseek_key == "sk-test-key-12345"

    def test_load_env_missing_file_raises(self):
        """load_env should raise RuntimeError if .env doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(project_root=Path(tmp))
            with pytest.raises(RuntimeError, match="does not exist"):
                cfg.load_env(env_file=Path(tmp) / "nonexistent.env")

    def test_load_env_missing_key_raises(self):
        """load_env should raise RuntimeError if DEEPSEEK_KEY is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("OTHER_KEY=some_value\n")

            cfg = Config(project_root=Path(tmp))
            with pytest.raises(RuntimeError, match="not found"):
                cfg.load_env(env_file=env_file)
