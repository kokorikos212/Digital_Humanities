"""
Conversation Analyzer — extracts conversation structure and pragmatics.

Uses Convokit to load corpora and compute politeness, toxicity, and
dialogue-act features.  Also accepts raw text for ad-hoc analysis of
user-supplied conversations outside a Convokit corpus.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config import config


# ── Input schema ──────────────────────────────────────────────────────────


class ConversationAnalyzerInput(BaseModel):
    """Input for the conversation analysis tool.

    Either provide a ``corpus_name`` + ``conversation_id`` to load from
    Convokit, or pass ``utterances`` directly for ad-hoc analysis.
    """

    corpus_name: Optional[str] = Field(
        None,
        description="Convokit corpus filename stem (e.g. 'conversations-gone-awry-corpus')",
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID to load from the corpus",
    )
    utterances: Optional[List[Dict[str, Any]]] = Field(
        None,
        description=(
            "Inline utterance list for ad-hoc analysis. "
            "Each dict: {id, speaker_id, text, reply_to?, timestamp?}"
        ),
    )
    include_pragmatics: bool = Field(
        True,
        description="Whether to compute politeness/toxicity features",
    )


# ── Tool implementation ───────────────────────────────────────────────────


class ConversationAnalyzer:
    """Analyse conversation structure, speaker dynamics, and pragmatics.

    Parameters
    ----------
    data_dir:
        Path to the directory containing Convokit corpus folders.
    """

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or str(config.data_dir)
        config.ensure_output_dirs()

    # ── Public tool method ────────────────────────────────────────────

    def analyze_conversation(
        self,
        corpus_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        utterances: Optional[List[Dict[str, Any]]] = None,
        include_pragmatics: bool = True,
    ) -> Dict[str, Any]:
        """Run conversation analysis.

        Returns a dict with ``conversation`` (structured data), ``speakers``,
        ``reply_graph``, ``pragmatic_summary``, and ``saved_at``.
        """
        conv_data: Dict[str, Any]

        if corpus_name and conversation_id:
            conv_data = self._from_corpus(corpus_name, conversation_id)
        elif utterances:
            conv_data = self._from_utterances(utterances)
        else:
            return {
                "error": "Either (corpus_name + conversation_id) or utterances must be provided."
            }

        if include_pragmatics:
            conv_data["pragmatic_summary"] = self._compute_pragmatics(conv_data)

        # Persist
        timestamp = int(time.time())
        filename = f"conversation_{conv_data.get('id', timestamp)}_{timestamp}.json"
        filepath = str(config.conversations_dir / filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, indent=2, default=str)

        conv_data["saved_at"] = filepath
        return conv_data

    # ── Corpus loading ────────────────────────────────────────────────

    def _from_corpus(
        self, corpus_name: str, conversation_id: str
    ) -> Dict[str, Any]:
        """Load and extract a single conversation from a Convokit corpus."""
        try:
            from convokit import Corpus

            corpus_path = str(config.data_dir / corpus_name)
            corpus = Corpus(filename=corpus_path)
            conv = corpus.get_conversation(conversation_id)

            return self._extract_convokit_conversation(conv, corpus_name)
        except Exception as e:
            return {
                "error": f"Failed to load conversation from corpus: {e}",
                "corpus_name": corpus_name,
                "conversation_id": conversation_id,
            }

    def _extract_convokit_conversation(
        self, conv, corpus_name: str
    ) -> Dict[str, Any]:
        """Pull structured data from a Convokit Conversation object."""
        utterances: List[Dict[str, Any]] = []
        speaker_ids: set = set()
        reply_graph: Dict[str, List[str]] = {}

        for utt in conv.iter_utterances():
            utt_data = {
                "id": str(utt.id),
                "speaker_id": str(utt.speaker.id if utt.speaker else "unknown"),
                "text": str(utt.text),
                "reply_to": str(utt.reply_to) if utt.reply_to else None,
                "timestamp": float(utt.timestamp) if utt.timestamp else None,
            }

            meta = getattr(utt, "meta", {}) or {}
            utt_data["meta"] = {
                k: v
                for k, v in meta.items()
                if not k.startswith("_") and not callable(v)
            }

            utterances.append(utt_data)
            speaker_ids.add(utt_data["speaker_id"])

            if utt_data["reply_to"]:
                reply_graph.setdefault(utt_data["reply_to"], []).append(
                    utt_data["id"]
                )

        speakers = []
        for sid in speaker_ids:
            try:
                sp = conv.get_speaker(sid)
                sp_meta = getattr(sp, "meta", {}) or {}
                speakers.append(
                    {
                        "id": str(sid),
                        "label": str(getattr(sp, "name", sid)),
                        "metadata": {
                            k: v
                            for k, v in sp_meta.items()
                            if not k.startswith("_") and not callable(v)
                        },
                    }
                )
            except Exception:
                speakers.append({"id": str(sid), "label": str(sid)})

        conv_meta = getattr(conv, "meta", {}) or {}
        metadata = {
            k: v
            for k, v in conv_meta.items()
            if not k.startswith("_") and not callable(v)
        }

        return {
            "id": str(conv.id),
            "corpus": corpus_name,
            "utterances": utterances,
            "speakers": speakers,
            "metadata": metadata,
            "reply_graph": reply_graph,
            "utterance_count": len(utterances),
            "speaker_count": len(speakers),
        }

    # ── Ad-hoc utterance processing ───────────────────────────────────

    def _from_utterances(
        self, utterances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process a user-supplied utterance list."""
        speakers: Dict[str, Dict[str, Any]] = {}
        reply_graph: Dict[str, List[str]] = {}

        clean_utterances = []
        for i, utt in enumerate(utterances):
            uid = utt.get("id", f"utt_{i}")
            sid = utt.get("speaker_id", "speaker_0")
            clean = {
                "id": str(uid),
                "speaker_id": str(sid),
                "text": str(utt.get("text", "")),
                "reply_to": str(utt["reply_to"]) if utt.get("reply_to") else None,
                "timestamp": utt.get("timestamp"),
            }
            clean_utterances.append(clean)

            if sid not in speakers:
                speakers[sid] = {
                    "id": str(sid),
                    "label": utt.get("speaker_label", str(sid)),
                }

            if clean["reply_to"]:
                reply_graph.setdefault(clean["reply_to"], []).append(clean["id"])

        return {
            "id": f"adhoc_{int(time.time())}",
            "corpus": None,
            "utterances": clean_utterances,
            "speakers": list(speakers.values()),
            "metadata": {},
            "reply_graph": reply_graph,
            "utterance_count": len(clean_utterances),
            "speaker_count": len(speakers),
        }

    # ── Pragmatics ────────────────────────────────────────────────────

    def _compute_pragmatics(
        self, conv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute pragmatic feature summaries across utterances."""
        summary: Dict[str, Any] = {
            "total_utterances": conv_data.get("utterance_count", 0),
            "utterances_with_replies": sum(
                1
                for u in conv_data.get("utterances", [])
                if u.get("reply_to") is not None
            ),
            "max_turn_depth": self._max_depth(conv_data.get("reply_graph", {})),
        }

        utts = conv_data.get("utterances", [])
        tox_scores = []
        has_attack = 0
        is_header = 0
        for u in utts:
            meta = u.get("meta", {})
            if "toxicity" in meta:
                try:
                    tox_scores.append(float(meta["toxicity"]))
                except (ValueError, TypeError):
                    pass
            if meta.get("comment_has_personal_attack") is True:
                has_attack += 1
            if meta.get("is_section_header") is True:
                is_header += 1

        if tox_scores:
            summary["toxicity"] = {
                "mean": sum(tox_scores) / len(tox_scores),
                "max": max(tox_scores),
                "min": min(tox_scores),
                "count": len(tox_scores),
            }
        summary["personal_attack_count"] = has_attack
        summary["section_header_count"] = is_header

        summary["dialogue_act_hints"] = self._heuristic_dialogue_acts(utts)

        return summary

    @staticmethod
    def _max_depth(reply_graph: Dict[str, List[str]]) -> int:
        """Compute the maximum depth of the reply tree."""
        if not reply_graph:
            return 0

        all_replies = {r for replies in reply_graph.values() for r in replies}
        roots = [uid for uid in reply_graph if uid not in all_replies]

        def dfs(node: str, depth: int) -> int:
            children = reply_graph.get(node, [])
            if not children:
                return depth
            return max(dfs(child, depth + 1) for child in children)

        if not roots:
            return 1 if reply_graph else 0
        return max(dfs(root, 1) for root in roots)

    @staticmethod
    def _heuristic_dialogue_acts(
        utterances: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Simple keyword-based dialogue act hints."""
        counts: Dict[str, int] = {
            "question": 0,
            "greeting": 0,
            "request": 0,
            "acknowledgment": 0,
        }
        for u in utterances:
            text = u.get("text", "").lower()
            if "?" in text:
                counts["question"] += 1
            if any(w in text for w in ("hello", "hi", "good morning", "good evening")):
                counts["greeting"] += 1
            if any(w in text for w in ("please", "could you", "would you")):
                counts["request"] += 1
            if any(w in text for w in ("thanks", "thank you", "okay", "got it")):
                counts["acknowledgment"] += 1
        return counts


# ── Registry helpers ──────────────────────────────────────────────────────

conversation_analyzer_registry = [
    ("analyze_conversation", ConversationAnalyzerInput),
]
