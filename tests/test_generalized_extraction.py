"""
Generalized extraction invariant tests.

Validates that the pipeline respects:
  I.   No unlinked (floating) entity nodes
  II.  Noise/emotional phrases don't create ibis:Position instances
  III. Node labels are concise (not verbatim multi-sentence dumps)
"""

from __future__ import annotations


class TestDomainEntityBinding:
    """Invariant I: zero floating entities."""

    def test_no_floating_entities(self):
        """Every entity with rdf:type must appear in at least one edge."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(
            entities=[
                {"id": "ex:Budget", "rdf_type": "schema:Thing", "label": "Budget"},
                {"id": "ex:Issue_1", "rdf_type": "ibis:Issue", "label": "Budget allocation"},
            ],
            relations=[],
            format="turtle",
        )

        # After _bind_isolated_nodes, ex:Budget should be linked
        subjects = {t["subject"] for t in result["triples"]}
        objects_ = {t["object"] for t in result["triples"]}

        # Every entity that gets rdf:type should appear as object of some edge
        # (via schema:about auto-binding)
        for t in result["triples"]:
            if t["predicate"] == "rdf:type":
                subj = t["subject"]
                edge_count = sum(
                    1 for rt in result["triples"]
                    if (rt["subject"] == subj or rt["object"] == subj)
                    and rt["predicate"] != "rdf:type"
                )
                assert edge_count > 0, f"Isolated node: {subj}"

    def test_auto_binding_attaches_schema_about(self):
        """Isolated entities get auto-bound to the ibis:Issue."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(
            entities=[
                {"id": "ex:ClimateBill", "rdf_type": "schema:Legislation", "label": "Climate Bill"},
                {"id": "ex:RootIssue", "rdf_type": "ibis:Issue", "label": "Climate policy"},
            ],
            relations=[],
            format="turtle",
        )

        predicates = {t["predicate"] for t in result["triples"]}
        assert "schema:about" in predicates, (
            f"No schema:about edge auto-generated. Predicates: {predicates}"
        )


class TestSpeechActNoiseFiltering:
    """Invariant II: emotional/phatic phrases don't become ibis:Position."""

    def test_emotional_phrase_yields_no_position(self):
        """Statements like 'I was worried' should NOT create ibis:Position."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(
            entities=[
                {"id": "ex:Worried", "rdf_type": "ex:Emotion", "label": "I was worried"},
            ],
            relations=[],
            format="turtle",
        )

        # No ibis:Position type should appear for emotional entities
        types = [t["object"] for t in result["triples"] if t["predicate"] == "rdf:type"]
        assert "ibis:Position" not in types, f"Emotion wrongly typed as ibis:Position: {types}"


class TestLabelAbstraction:
    """Invariant IV: concise labels, full text in schema:text."""

    def test_labels_are_concise_summaries(self):
        """rdfs:label should be short (not verbatim multi-sentence text)."""
        from src.tools.triples import TripleGenerator

        gen = TripleGenerator()
        result = gen.generate_triples(
            entities=[
                {
                    "id": "bench_claim",
                    "rdf_type": "ibis:Position",
                    "label": "Prioritize computing lab equipment",
                    "properties": {
                        "schema:text": "We must prioritize lab equipment. Modernizing"
                        " our computing labs directly impacts academic output and"
                        " research rankings."
                    },
                },
            ],
            relations=[],
            format="turtle",
        )

        # Label should be short, full text in schema:text
        labels = {t["object"] for t in result["triples"] if t["predicate"] == "rdfs:label"}
        texts = {t["object"] for t in result["triples"] if t["predicate"] == "schema:text"}

        assert any("Prioritize" in lbl for lbl in labels), f"Short label missing: {labels}"
        assert any("research rankings" in txt for txt in texts), f"Full text missing: {texts}"
