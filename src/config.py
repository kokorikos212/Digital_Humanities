"""
Centralized configuration for the ontological analysis pipeline.

All paths, API settings, and defaults live here.  Nothing reads from
disk or the environment until ``config.load_env()`` is called, so
importing this module is side-effect-free.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Single source of truth for all pipeline settings.

    Usage::

        from src.config import config
        config.load_env()
        client = openai.OpenAI(api_key=config.deepseek_key, base_url=config.deepseek_base_url)
    """

    # ── Paths ──────────────────────────────────────────────────────────

    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )

    @property
    def output_dir(self) -> Path:
        return self.project_root / "output"

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def graphs_dir(self) -> Path:
        return self.output_dir / "graphs"

    @property
    def rdf_dir(self) -> Path:
        return self.output_dir / "rdf"

    @property
    def conversations_dir(self) -> Path:
        return self.output_dir / "conversations"

    @property
    def verse_dir(self) -> Path:
        return self.output_dir / "verse"

    # ── API settings ───────────────────────────────────────────────────

    deepseek_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    max_iterations: int = 30

    # ── NLP settings ───────────────────────────────────────────────────

    spacy_model: str = "en_core_web_sm"

    # ── Methods ────────────────────────────────────────────────────────

    def load_env(self, env_file: Path | None = None) -> None:
        """Load ``DEEPSEEK_KEY`` from the project ``.env`` file.

        Parameters
        ----------
        env_file:
            Optional explicit path to a ``.env`` file.  Defaults to
            ``<project_root>/.env``.
        """
        if env_file is None:
            env_file = self.project_root / ".env"

        if not env_file.exists():
            raise RuntimeError(
                f"DEEPSEEK_KEY not found.  {env_file} does not exist.  "
                "Copy .env.example to .env and add your key."
            )

        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_KEY="):
                    self.deepseek_key = line.split("=", 1)[1].strip()
                    return

        raise RuntimeError(
            "DEEPSEEK_KEY not found in .env file.  "
            "Add `DEEPSEEK_KEY=sk-...` to your .env file."
        )

    def ensure_output_dirs(self) -> None:
        """Create all output subdirectories if they don't exist."""
        for d in [
            self.output_dir,
            self.graphs_dir,
            self.rdf_dir,
            self.conversations_dir,
            self.verse_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


# Singleton instance — call ``config.load_env()`` once at startup.
config = Config()
