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

    # ── LLM provider ────────────────────────────────────────────────────

    provider: str = "deepseek"  # deepseek | huggingface | groq | ollama
    model: str = "deepseek-chat"
    max_iterations: int = 30

    # ── Provider-specific keys & endpoints ──────────────────────────────

    deepseek_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    huggingface_key: str = ""
    huggingface_base_url: str = "https://api-inference.huggingface.co/models/"

    groq_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    ollama_base_url: str = "http://localhost:11434/v1"

    @property
    def api_key(self) -> str:
        """Return the active provider's API key."""
        return getattr(self, f"{self.provider}_key", self.deepseek_key)

    @property
    def api_base_url(self) -> str:
        """Return the active provider's base URL."""
        return getattr(self, f"{self.provider}_base_url", self.deepseek_base_url)

    # ── NLP settings ───────────────────────────────────────────────────

    spacy_model: str = "en_core_web_sm"

    # ── Methods ────────────────────────────────────────────────────────

    def load_env(self, env_file: Path | None = None) -> None:
        """Load API keys from the project ``.env`` file.

        Supports ``DEEPSEEK_KEY``, ``HF_TOKEN``, ``GROQ_API_KEY``,
        ``OLLAMA_BASE_URL``, and ``BYTEZ_API_KEY``.

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


# ── Multi-tenant project path helpers ─────────────────────────────────────


def resolve_project_dir(user_id: str, project_id: str) -> Path:
    """Return the absolute path to a user project root, creating dirs if missing."""
    base = config.project_root / "data" / "users" / user_id / "projects" / project_id
    (base / "documents").mkdir(parents=True, exist_ok=True)
    (base / "notes").mkdir(parents=True, exist_ok=True)
    (base / "graphs").mkdir(parents=True, exist_ok=True)
    return base


def resolve_documents_dir(user_id: str, project_id: str) -> Path:
    """Return the documents subdirectory for a user project."""
    return resolve_project_dir(user_id, project_id) / "documents"


# Singleton instance — call ``config.load_env()`` once at startup.
config = Config()
