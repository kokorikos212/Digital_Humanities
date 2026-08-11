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

    # ── LLM provider (env-var driven) ────────────────────────────────────

    llm_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_KEY") or os.getenv("LLM_API_KEY", "")
    )
    llm_base_url: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-chat")
    )
    bytez_key: str = field(default_factory=lambda: os.getenv("BYTEZ_API_KEY", ""))
    bytez_vl_model: str = field(
        default_factory=lambda: os.getenv("BYTEZ_VL_MODEL", "Salesforce/blip2-opt-2.7b")
    )
    bytez_api_url: str = field(
        default_factory=lambda: os.getenv("BYTEZ_API_URL", "https://api.bytez.com/v1/model/run")
    )
    max_iterations: int = 30

    # Legacy compat
    @property
    def deepseek_key(self) -> str:
        return self.llm_api_key

    @property
    def deepseek_base_url(self) -> str:
        return self.llm_base_url

    @property
    def model(self) -> str:
        return self.llm_model

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
                f"API key not found.  {env_file} does not exist.  "
                "Copy .env.example to .env and add your key."
            )

        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_KEY=") or line.startswith("LLM_API_KEY="):
                    self.llm_api_key = line.split("=", 1)[1].strip()
                elif line.startswith("BYTEZ_API_KEY="):
                    self.bytez_key = line.split("=", 1)[1].strip()
                elif line.startswith("LLM_BASE_URL="):
                    self.llm_base_url = line.split("=", 1)[1].strip()
                elif line.startswith("LLM_MODEL="):
                    self.llm_model = line.split("=", 1)[1].strip()

        if not self.llm_api_key:
            raise RuntimeError(
                "API key not found in .env file.  "
                "Add `DEEPSEEK_KEY=sk-...` or `LLM_API_KEY=...` to your .env file."
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
