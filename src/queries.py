"""
Case-aware SPARQL query registry mapped to pre-computed benchmark cases.

Each case exposes one or more use-case-specific queries.
"""

import rdflib
import pandas as pd
from typing import Dict

# ── Case-query registry ─────────────────────────────────────────────────────

_CASE_ALIASES: Dict[str, str] = {
    "bench_1_1_rebuttal": "Case 1: University Budget Debate",
    "bench_5_2_nested_conditional": "Case 2: Modal & Conditional Claims (Dr. Aris)",
    "ex_ontology_basic": "Case 3: Reified Events (Dr. Chen Presentation)",
}

CASE_QUERIES: Dict[str, Dict[str, str]] = {
    "Case 1: University Budget Debate": {
        "Use Case 1: Conflict Density Indexing": """
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX aif:    <http://www.arg.tech/aif#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?issueLabel ?speakerLabel ?positionLabel ?targetPositionLabel
WHERE {
  ?issue a ibis:Issue ;
         rdfs:label ?issueLabel .

  ?position a ibis:Position ;
            ibis:respondsTo ?issue ;
            rdfs:label ?positionLabel ;
            prov:wasAttributedTo ?speaker .

  ?speaker rdfs:label ?speakerLabel .

  OPTIONAL {
    ?position ibis:rebuts ?targetPosition .
    ?targetPosition rdfs:label ?targetPositionLabel .
  }
}
ORDER BY ?issueLabel ?speakerLabel
""",
        "Use Case 2: Policy Need vs. Priority Audit (Auto-Bound Entities)": """
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?issueLabel ?entity ?entityLabel ?entityType
WHERE {
  ?issue a ibis:Issue ;
         rdfs:label ?issueLabel .

  ?issue schema:about ?entity .

  ?entity rdfs:label ?entityLabel ;
          a ?entityType .
}
""",
    },

    "Case 2: Modal & Conditional Claims (Dr. Aris)": {
        "Use Case 1: Reified Claims & Speaker Attribution": """
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX aif:    <http://www.arg.tech/aif#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?speakerName ?jobTitle ?shortClaimLabel ?fullClaimText
WHERE {
  ?speaker a schema:Person ;
           rdfs:label ?speakerName ;
           ibis:asserts ?claim .

  OPTIONAL { ?speaker schema:jobTitle ?jobTitle . }

  ?claim a ibis:Position ;
         rdfs:label ?shortClaimLabel ;
         aif:claimText ?fullClaimText .
}
""",
        "Use Case 2: Protasis/Apodosis Sub-Triple Decomposition": """
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX aif:    <http://www.arg.tech/aif#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?claimLabel ?subEntityLabel ?relation ?targetEntityLabel
WHERE {
  ?claim a aif:I-node ;
         rdfs:label ?claimLabel ;
         schema:about ?subEntity .

  ?subEntity rdfs:label ?subEntityLabel .

  OPTIONAL {
    ?subEntity ?relation ?targetEntity .
    ?targetEntity rdfs:label ?targetEntityLabel .
    FILTER(?relation != rdfs:label && ?relation != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
  }
}
""",
    },

    "Talos General SPARQL Presets": {
        "Explore All Triples (LIMIT 10)": """
SELECT * WHERE { ?s ?p ?o } LIMIT 10
""",
        "List All Entity Types": """
SELECT DISTINCT ?type WHERE { ?s a ?type }
""",
        "List Labels (LIMIT 20)": """
SELECT ?s ?label WHERE { ?s rdfs:label ?label } LIMIT 20
""",
        "CONSTRUCT Sub-Graph (LIMIT 50)": """
CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 50
""",
    },

    "Case 3: Reified Events (Dr. Chen Presentation)": {
        "Use Case 1: Event-Centric Activity Resolution": """
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?activityLabel ?agentName ?locationName ?startTime ?usedArtifact
WHERE {
  ?activity a prov:Activity ;
            rdfs:label ?activityLabel ;
            prov:wasAssociatedWith ?agent .

  ?agent rdfs:label ?agentName .

  OPTIONAL {
    ?activity schema:location ?location .
    ?location rdfs:label ?locationName .
  }

  OPTIONAL { ?activity prov:startedAtTime ?startTime . }
  OPTIONAL {
    ?activity prov:used ?artifact .
    ?artifact rdfs:label ?usedArtifact .
  }
}
""",
    },
}

# Flattened for backward-compatible dropdown access
PRESET_SPARQL_QUERIES: Dict[str, str] = {}
for _case_queries in CASE_QUERIES.values():
    PRESET_SPARQL_QUERIES.update(_case_queries)


# ── SPARQL executor ─────────────────────────────────────────────────────────

def execute_sparql(ttl_code: str, query_str: str) -> pd.DataFrame:
    """Execute a SPARQL query against a Turtle string and return a DataFrame."""
    if not ttl_code or not query_str:
        return pd.DataFrame()

    g = rdflib.Graph()
    try:
        g.parse(data=ttl_code, format="turtle")
        results = g.query(query_str)
        cols = [str(var) for var in results.vars]
        data = [[str(val) if val is not None else "" for val in row] for row in results]
        return pd.DataFrame(data, columns=cols)
    except Exception as e:
        return pd.DataFrame([{"Error": f"SPARQL Execution Failed: {str(e)}"}])


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_queries_for_case(case_title: str) -> Dict[str, str]:
    """Return the query map for a specific case, falling back to Talos general presets."""
    real = _CASE_ALIASES.get(case_title, case_title)
    return CASE_QUERIES.get(real, CASE_QUERIES.get("Talos General SPARQL Presets", {}))
