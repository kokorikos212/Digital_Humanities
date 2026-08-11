"""
SPARQL query registry tests — case-aware queries + DataFrame conversion.
"""

import json
import tempfile
from pathlib import Path

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


class TestCaseAwareQueries:
    """Verify CASE_QUERIES registry and execute_sparql."""

    def test_get_queries_for_case_known(self):
        from src.queries import get_queries_for_case, CASE_QUERIES

        qs = get_queries_for_case("Case 1: University Budget Debate")
        assert len(qs) == 2
        assert "Use Case 1: Conflict Density Indexing" in qs

    def test_get_queries_for_case_unknown_falls_back(self):
        from src.queries import get_queries_for_case

        qs = get_queries_for_case("nonexistent")
        assert isinstance(qs, dict)
        assert len(qs) == 4  # Talos General SPARQL Presets
        assert "Explore All Triples (LIMIT 10)" in qs

    def test_execute_sparql_all_cases(self):
        from src.queries import CASE_QUERIES, execute_sparql

        for case_title, queries in CASE_QUERIES.items():
            for use_case, query in queries.items():
                df = execute_sparql(SAMPLE_TTL, query)
                assert hasattr(df, "columns"), (
                    f"{case_title}/{use_case} did not return DataFrame"
                )

    def test_execute_sparql_empty_inputs(self):
        from src.queries import execute_sparql

        assert execute_sparql("", "").empty
        assert execute_sparql(SAMPLE_TTL, "").empty

    def test_case1_budget_finds_rebuttal(self):
        from src.queries import CASE_QUERIES, execute_sparql

        queries = CASE_QUERIES["Case 1: University Budget Debate"]
        df = execute_sparql(SAMPLE_TTL, queries[
            "Use Case 1: Conflict Density Indexing"
        ])
        assert len(df) >= 1
        assert any("Maria" in str(row) for row in df.values)

    def test_case1_entity_audit_finds_bound_entities(self):
        from src.queries import CASE_QUERIES, execute_sparql

        queries = CASE_QUERIES["Case 1: University Budget Debate"]
        df = execute_sparql(SAMPLE_TTL, queries[
            "Use Case 2: Policy Need vs. Priority Audit (Auto-Bound Entities)"
        ])
        assert len(df) >= 1
        assert any("Lab Equipment" in str(row) for row in df.values)
