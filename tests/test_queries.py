"""
SPARQL query registry tests — syntax validation & DataFrame conversion.
"""

import pytest

SAMPLE_TTL = """
@prefix ibis:  <http://purl.org/ibis#> .
@prefix aif:   <http://www.arg.tech/aif#> .
@prefix prov:  <http://www.w3.org/ns/prov#> .
@prefix schema:<http://schema.org/> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:    <http://example.org/ontology/> .

ex:BudgetIssue a ibis:Issue ;
    rdfs:label "Budget allocation" .

ex:LabEquipment a schema:Thing ;
    rdfs:label "Lab Equipment" .

ex:BudgetIssue schema:about ex:LabEquipment .

ex:Rep_Alex a schema:Person ;
    rdfs:label "Representative Alex" ;
    ibis:asserts ex:Claim_LabEquipment .

ex:Claim_LabEquipment a ibis:Position, aif:I-node ;
    rdfs:label "Prioritize lab equipment" ;
    aif:claimText "We must prioritize lab equipment." ;
    ibis:respondsTo ex:BudgetIssue ;
    prov:wasAttributedTo ex:Rep_Alex ;
    schema:about ex:LabEquipment .

ex:Rep_Maria a schema:Person ;
    rdfs:label "Representative Maria" ;
    ibis:asserts ex:Claim_Housing .

ex:Claim_Housing a ibis:Position ;
    rdfs:label "Housing subsidies must come first" ;
    ibis:respondsTo ex:BudgetIssue ;
    ibis:rebuts ex:Claim_LabEquipment ;
    prov:wasAttributedTo ex:Rep_Maria .

ex:Presentation a prov:Activity ;
    rdfs:label "Budget presentation" ;
    prov:wasAssociatedWith ex:Rep_Alex ;
    prov:startedAtTime "2026-08-04"^^xsd:date .

ex:Hub_Legitimacy a skos:Concept ;
    rdfs:label "Legitimacy" ;
    schema:about ex:BudgetIssue .
"""


class TestSPARQLQueries:
    """Verify every preset query compiles and returns results."""

    def test_all_queries_parse(self):
        """Every PRESET_SPARQL_QUERIES entry executes without syntax errors."""
        from src.queries import PRESET_SPARQL_QUERIES
        from src.visualizer import execute_sparql_query

        for name, query in PRESET_SPARQL_QUERIES.items():
            df = execute_sparql_query(SAMPLE_TTL, query)
            assert hasattr(df, "columns"), (
                f"Query '{name}' did not return a DataFrame"
            )

    def test_case_1_1_finds_rebuttal(self):
        """Case 1.1 should find Maria rebutting Alex's claim."""
        from src.queries import PRESET_SPARQL_QUERIES
        from src.visualizer import execute_sparql_query

        df = execute_sparql_query(SAMPLE_TTL, PRESET_SPARQL_QUERIES[
            "Case 1.1: Budget Debate — Conflict & Rebuttal Topology"
        ])
        assert len(df) >= 1
        assert any("Maria" in str(row) for row in df.values)

    def test_case_1_2_finds_bound_entities(self):
        """Case 1.2 should find budget issue with schema:about entity."""
        from src.queries import PRESET_SPARQL_QUERIES
        from src.visualizer import execute_sparql_query

        df = execute_sparql_query(SAMPLE_TTL, PRESET_SPARQL_QUERIES[
            "Case 1.2: Audit Auto-Bound Entities to Root Issue"
        ])
        assert len(df) >= 1
        assert any("Lab Equipment" in str(row) for row in df.values)

    def test_case_3_1_finds_activity(self):
        """Case 3.1 should find the presentation event with agent binding."""
        from src.queries import PRESET_SPARQL_QUERIES
        from src.visualizer import execute_sparql_query

        df = execute_sparql_query(SAMPLE_TTL, PRESET_SPARQL_QUERIES[
            "Case 3.1: Event-Centric Activity Resolution (prov:Activity)"
        ])
        assert len(df) >= 1
        assert any("Budget presentation" in str(row) for row in df.values)

    def test_metric_4_2_finds_hub_node(self):
        """Metric 4.2 should find the skos:Concept hub node."""
        from src.queries import PRESET_SPARQL_QUERIES
        from src.visualizer import execute_sparql_query

        df = execute_sparql_query(SAMPLE_TTL, PRESET_SPARQL_QUERIES[
            "Metric 4.2: Hub-Node Weighting (W_hub) Extraction via SKOS"
        ])
        assert len(df) >= 1
        assert any("Legitimacy" in str(row) for row in df.values)

    def test_execute_empty_inputs(self):
        """Empty inputs return empty DataFrame."""
        from src.visualizer import execute_sparql_query

        df = execute_sparql_query("", "")
        assert df.empty

        df2 = execute_sparql_query(SAMPLE_TTL, "")
        assert df2.empty
