"""
Centralized SPARQL query registry for benchmark evaluation cases.

Each query targets a specific ontological extraction dimension:
  - Case 1.x: Rebuttal topology & entity binding
  - Case 2.x: Claim attribution & decomposition
  - Case 3.x: Event-centric activity resolution
  - Metric 4.x: Node divergence & hub-node weighting
"""

PRESET_SPARQL_QUERIES = {
    "Case 1.1: Budget Debate — Conflict & Rebuttal Topology": """
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

    "Case 1.2: Audit Auto-Bound Entities to Root Issue": """
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

    "Case 2.1: Reified Claims & Speaker Attribution": """
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

    "Case 2.2: Decomposed Protasis/Apodosis Sub-Triples": """
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

    "Case 3.1: Event-Centric Activity Resolution (prov:Activity)": """
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

    "Metric 4.1: Computing Node Divergence (D_nd) Baseline": """
PREFIX ibis:   <http://purl.org/ibis#>
PREFIX aif:    <http://www.arg.tech/aif#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?issueLabel ?faction1 ?pos1Label ?pos2Label
WHERE {
  ?issue a ibis:Issue ;
         rdfs:label ?issueLabel .

  ?pos1 ibis:respondsTo ?issue ;
        prov:wasAttributedTo ?faction1 ;
        rdfs:label ?pos1Label ;
        ibis:rebuts ?pos2 .

  ?pos2 ibis:respondsTo ?issue ;
        rdfs:label ?pos2Label .
}
""",

    "Metric 4.2: Hub-Node Weighting (W_hub) Extraction via SKOS": """
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?concept ?conceptLabel (COUNT(?connectedNode) AS ?degreeCentrality)
WHERE {
  ?concept a skos:Concept ;
           rdfs:label ?conceptLabel .

  { ?concept ?p ?connectedNode . }
  UNION
  { ?connectedNode ?p2 ?concept . }
}
GROUP BY ?concept ?conceptLabel
ORDER BY DESC(?degreeCentrality)
""",
}
