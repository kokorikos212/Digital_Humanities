"""
Isolated unit tests for each tool handler.

All tests run OFFLINE — no DeepSeek API call, no network required.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.config import Config


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_TEXT = (
    "Dr. Chen presented the research findings at Stanford University "
    "last Tuesday. The professor argued that machine learning models "
    "can detect bias in political speeches."
)

SAMPLE_CONVERSATION = (
    "Alice: Hello Professor! Could you review my thesis?\n"
    "Bob: Of course, Alice. I'll have comments by Friday."
)

SAMPLE_ENTITIES = [
    {"id": "Dr_Chen", "rdf_type": "ex:Speaker", "label": "Dr. Chen",
     "properties": {"ex:hasName": "Dr. Chen"}},
    {"id": "Stanford_University", "rdf_type": "ex:NamedEntity",
     "label": "Stanford University", "properties": {"ex:hasType": "ORG"}},
]

SAMPLE_RELATIONS = [
    {"subject": "Dr_Chen", "predicate": "ex:presentedAt",
     "object": "Stanford_University"},
]


def _temp_config() -> Config:
    """Create a Config pointing at a temporary directory."""
    tmp = tempfile.mkdtemp()
    return Config(project_root=Path(tmp))


# ═══════════════════════════════════════════════════════════════════════════
# Linguistic Tool
# ═══════════════════════════════════════════════════════════════════════════


class TestLinguisticTool:
    """Tests for src/tools/linguistics.py — spaCy POS/NER/dependency parsing."""

    def test_get_tags_returns_expected_keys(self):
        """get_tags should return a dict with all expected top-level keys."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.get_tags(SAMPLE_TEXT)

        assert isinstance(result, dict)
        for key in ["text", "tokens", "entities", "dependencies",
                     "noun_chunks", "root_verb"]:
            assert key in result, f"Missing key: {key}"

    def test_get_tags_extracts_tokens(self):
        """Token list should contain dicts with linguistic annotation."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.get_tags(SAMPLE_TEXT)

        tokens = result["tokens"]
        assert len(tokens) > 0
        first = tokens[0]
        for field in ["index", "text", "lemma", "pos", "tag", "dep", "head"]:
            assert field in first, f"Token missing field: {field}"

    def test_get_tags_finds_named_entities(self):
        """Should detect PERSON, ORG, GPE entities in the sample text."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.get_tags(SAMPLE_TEXT)

        entities = result["entities"]
        assert len(entities) > 0
        entity_labels = {e["label"] for e in entities}
        assert "PERSON" in entity_labels or "ORG" in entity_labels or "GPE" in entity_labels

    def test_get_tags_extracts_dependencies(self):
        """Dependency edges should have source, target, relation fields."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.get_tags(SAMPLE_TEXT)

        deps = result["dependencies"]
        assert len(deps) > 0
        for dep in deps:
            assert "source" in dep
            assert "target" in dep
            assert "relation" in dep

    def test_generate_viz_creates_svg_file(self):
        """generate_viz should save an SVG file."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.generate_viz(SAMPLE_TEXT, style="dep")

        assert result["status"] == "success"
        assert Path(result["saved_at"]).exists()
        assert Path(result["saved_at"]).suffix == ".svg"

    def test_get_tags_handles_empty_text(self):
        """Should not crash on empty text."""
        from src.tools.linguistics import LinguisticTools

        tool = LinguisticTools()
        result = tool.get_tags("")
        assert result["text"] == ""
        assert result["tokens"] == []
        assert result["entities"] == []


# ═══════════════════════════════════════════════════════════════════════════
# Triple Generator Tool
# ═══════════════════════════════════════════════════════════════════════════


class TestTripleGenerator:
    """Tests for src/tools/triples.py — RDF triple generation."""

    def test_generate_triples_returns_expected_keys(self):
        """generate_triples should return dict with triples, serialized, etc."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(SAMPLE_ENTITIES, SAMPLE_RELATIONS)

        for key in ["triples", "serialized", "saved_at", "format", "count"]:
            assert key in result, f"Missing key: {key}"

    def test_triples_saved_to_file(self):
        """The serialized RDF should be saved to disk."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(SAMPLE_ENTITIES, SAMPLE_RELATIONS)

        saved = Path(result["saved_at"])
        assert saved.exists()
        content = saved.read_text()
        assert len(content) > 0

    def test_triple_count_includes_rdf_type_and_label(self):
        """Each entity gets rdf:type + rdfs:label triples automatically."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(SAMPLE_ENTITIES, [])

        # 2 entities × 2 auto triples (type + label) + 1 property per entity
        # = 2 + 2 + 1 + 1 = 6
        triples = result["triples"]
        subjects = {t["subject"] for t in triples}
        predicates = {t["predicate"] for t in triples}

        assert "rdf:type" in predicates, "Should have rdf:type triples"
        assert "rdfs:label" in predicates, "Should have rdfs:label triples"
        assert result["count"] >= 4

    def test_turtle_output_contains_prefix_declarations(self):
        """Turtle serialization should include @prefix lines."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(SAMPLE_ENTITIES, [],
                                       format="turtle")

        assert "@prefix" in result["serialized"]

    def test_empty_inputs_produce_minimal_output(self):
        """Empty entities/relations should not crash."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples([], [], format="turtle")
        assert result["count"] == 0
        assert isinstance(result["serialized"], str)


# ═══════════════════════════════════════════════════════════════════════════
# Graph Builder Tool
# ═══════════════════════════════════════════════════════════════════════════


class TestGraphBuilder:
    """Tests for src/tools/graph.py — networkx + pyvis semantic graphs."""

    def test_generate_semantic_graph_returns_expected_keys(self):
        """Should return saved_at, node_count, edge_count, summary."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph(
            SAMPLE_ENTITIES, SAMPLE_RELATIONS, title="Test Graph"
        )

        for key in ["saved_at", "node_count", "edge_count", "summary"]:
            assert key in result, f"Missing key: {key}"

    def test_graph_html_file_is_created(self):
        """The output should be an HTML file on disk."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph(
            SAMPLE_ENTITIES, SAMPLE_RELATIONS, title="Test Graph"
        )

        saved = Path(result["saved_at"])
        assert saved.exists()
        assert saved.suffix == ".html"
        content = saved.read_text()
        assert "<html" in content.lower() or "<!DOCTYPE" in content.upper()

    def test_node_count_matches_entities(self):
        """Node count should equal the number of input entities."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph(
            SAMPLE_ENTITIES, SAMPLE_RELATIONS
        )

        assert result["node_count"] == len(SAMPLE_ENTITIES)

    def test_edge_count_matches_relations(self):
        """Edge count should equal the number of input relations."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph(
            SAMPLE_ENTITIES, SAMPLE_RELATIONS
        )

        assert result["edge_count"] == len(SAMPLE_RELATIONS)

    def test_empty_inputs_produce_empty_graph(self):
        """Should handle empty entities/relations gracefully."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph([], [], title="Empty")

        assert result["node_count"] == 0
        assert result["edge_count"] == 0
        assert Path(result["saved_at"]).exists()

    def test_hierarchical_layout(self):
        """Should accept hierarchical layout without error."""
        from src.tools.graph import GraphBuilder

        builder = GraphBuilder()
        result = builder.generate_semantic_graph(
            SAMPLE_ENTITIES, SAMPLE_RELATIONS,
            title="Hierarchical", layout="hierarchical"
        )

        assert result["node_count"] == len(SAMPLE_ENTITIES)


# ═══════════════════════════════════════════════════════════════════════════
# Obsidian Builder Tool
# ═══════════════════════════════════════════════════════════════════════════


class TestObsidianBuilder:
    """Tests for src/tools/obsidian.py — Obsidian note generation."""

    def test_build_obsidian_note_returns_expected_keys(self):
        """Should return filename, saved_at, wikilinks, frontmatter, etc."""
        from src.tools.obsidian import ObsidianBuilder

        builder = ObsidianBuilder()
        result = builder.build_obsidian_note(
            filename="test_note.md",
            note_type="TestAnalysis",
            entity_data={"rdf_type": "ex:Concept", "source_prompt": "test"},
            entities=SAMPLE_ENTITIES,
            body_sections=[{"heading": "Summary", "content": "Test content."}],
            tags=["test"],
        )

        for key in ["filename", "saved_at", "wikilinks",
                     "frontmatter_preview", "character_count"]:
            assert key in result, f"Missing key: {key}"

    def test_output_file_exists_and_has_frontmatter(self):
        """The saved .md file should have YAML frontmatter."""
        from src.tools.obsidian import ObsidianBuilder

        builder = ObsidianBuilder()
        result = builder.build_obsidian_note(
            filename="test_frontmatter.md",
            note_type="TestAnalysis",
            entity_data={"rdf_type": "ex:Utterance"},
            entities=SAMPLE_ENTITIES,
            body_sections=[{"heading": "Section", "content": "Body content"}],
        )

        saved = Path(result["saved_at"])
        assert saved.exists()
        content = saved.read_text()
        assert content.startswith("---"), "Should start with YAML frontmatter"
        assert "ex:Utterance" in content
        assert "## Section" in content
        assert "Body content" in content

    def test_wikilinks_are_extracted(self):
        """[[wikilinks]] in the body should be detected."""
        from src.tools.obsidian import ObsidianBuilder

        builder = ObsidianBuilder()
        result = builder.build_obsidian_note(
            filename="wikilinks_test.md",
            entities=SAMPLE_ENTITIES,
            body_sections=[{"heading": "Links", "content": "See [[Dr_Chen]]"}],
        )

        assert "Dr_Chen" in result["wikilinks"]

    def test_filename_sanitization(self):
        """Unsafe characters in filenames should be replaced."""
        from src.tools.obsidian import ObsidianBuilder

        builder = ObsidianBuilder()
        result = builder.build_obsidian_note(
            filename="unsafe/../name.md",
        )

        assert "/" not in result["filename"]
        assert result["filename"].endswith(".md")

    def test_default_values_produce_valid_output(self):
        """Minimal input should still produce a valid note."""
        from src.tools.obsidian import ObsidianBuilder

        builder = ObsidianBuilder()
        result = builder.build_obsidian_note(filename="minimal.md")

        assert Path(result["saved_at"]).exists()
        assert result["character_count"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# Writer Tool
# ═══════════════════════════════════════════════════════════════════════════


class TestWriterTool:
    """Tests for src/tools/writer.py — restricted file writer."""

    def test_write_file_saves_markdown(self):
        """Should write .md content to disk."""
        from src.tools.writer import FolderRestrictedAgent

        writer = FolderRestrictedAgent()
        result = writer.write_file("test_report.md", "# Hello\n\nWorld.")

        assert "Successfully saved" in result
        saved_path = Path(result.split("Successfully saved to ")[1])
        assert saved_path.exists()
        assert saved_path.read_text() == "# Hello\n\nWorld."

    def test_non_md_extension_is_rejected(self):
        """Only .md files should be allowed."""
        from src.tools.writer import FolderRestrictedAgent

        writer = FolderRestrictedAgent()
        result = writer.write_file("../../../evil.txt", "bad")

        assert "Tool Error" in result or "Only .md" in result

    def test_export_graph_html_empty_data(self):
        """export_graph_html with empty data returns error."""
        from src.tools.writer import FolderRestrictedAgent

        writer = FolderRestrictedAgent()
        result = writer.export_graph_html("", "test")
        assert "Tool Error" in result

    def test_export_graph_html_creates_file(self):
        """export_graph_html with valid TTL creates an HTML file."""
        from src.tools.writer import FolderRestrictedAgent

        ttl = """
        @prefix ex: <http://example.org/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:A a ex:Thing ; rdfs:label "Test" .
        """
        writer = FolderRestrictedAgent()
        result = writer.export_graph_html(ttl, "test_graph")
        assert "Graph exported to" in result
        saved_path = Path(result.split("Graph exported to ")[1])
        assert saved_path.exists()
        content = saved_path.read_text()
        assert "<html" in content.lower() or "pyvis" in content.lower()
        assert "Test" in content


# ═══════════════════════════════════════════════════════════════════════════
# Conversation Analyzer (ad-hoc mode, no Convokit required)
# ═══════════════════════════════════════════════════════════════════════════


class TestConversationAnalyzer:
    """Tests for src/tools/conversation.py — ad-hoc mode (no Convokit)."""

    def test_analyze_with_utterances(self):
        """Should process ad-hoc utterances without Convokit."""
        from src.tools.conversation import ConversationAnalyzer

        analyzer = ConversationAnalyzer()
        result = analyzer.analyze_conversation(
            utterances=[
                {"id": "1", "speaker_id": "A", "text": "Hello!"},
                {"id": "2", "speaker_id": "B", "text": "Hi there!",
                 "reply_to": "1"},
            ]
        )

        assert "error" not in result
        assert result["utterance_count"] == 2
        assert result["speaker_count"] == 2
        assert "1" in result["reply_graph"]
        assert result["reply_graph"]["1"] == ["2"]

    def test_missing_input_returns_error(self):
        """Should return error when neither corpus nor utterances given."""
        from src.tools.conversation import ConversationAnalyzer

        analyzer = ConversationAnalyzer()
        result = analyzer.analyze_conversation()

        assert "error" in result

    def test_result_is_saved_to_file(self):
        """The analysis should be persisted to disk."""
        from src.tools.conversation import ConversationAnalyzer

        analyzer = ConversationAnalyzer()
        result = analyzer.analyze_conversation(
            utterances=[
                {"id": "1", "speaker_id": "A", "text": "Test."},
            ]
        )

        assert "saved_at" in result
        assert Path(result["saved_at"]).exists()
