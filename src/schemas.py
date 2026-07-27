"""
Output schemas for the ontological conversation analysis pipeline.

These Pydantic models define the structured representations that the agent
produces: linguistic annotations, conversation structure, RDF triples,
Obsidian-ready notes, and the top-level OntologicalAnalysis envelope.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# Ontology Vocabulary
# ═══════════════════════════════════════════════════════════════════════════


class OntologyPrefix(str, Enum):
    """Standard namespace prefixes used in the ontology."""

    RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    RDFS = "http://www.w3.org/2000/01/rdf-schema#"
    OWL = "http://www.w3.org/2002/07/owl#"
    EX = "http://example.org/ontology/"
    CONVOKIT = "http://convokit.cornell.edu/ontology/"
    NIF = "http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#"
    PROV = "http://www.w3.org/ns/prov#"


class EntityType(str, Enum):
    """The rdf:type values for ontological entities."""

    CONVERSATION = "ex:Conversation"
    UTTERANCE = "ex:Utterance"
    SPEAKER = "ex:Speaker"
    NAMED_ENTITY = "ex:NamedEntity"
    LINGUISTIC_CONCEPT = "ex:LinguisticConcept"
    PRAGMATIC_FEATURE = "ex:PragmaticFeature"
    DEPENDENCY_RELATION = "ex:DependencyRelation"
    DISCOURSE_MARKER = "ex:DiscourseMarker"


class POSTag(str, Enum):
    """Common Universal Dependencies POS tags."""

    ADJ = "ADJ"
    ADP = "ADP"
    ADV = "ADV"
    AUX = "AUX"
    CCONJ = "CCONJ"
    DET = "DET"
    INTJ = "INTJ"
    NOUN = "NOUN"
    NUM = "NUM"
    PART = "PART"
    PRON = "PRON"
    PROPN = "PROPN"
    PUNCT = "PUNCT"
    SCONJ = "SCONJ"
    SYM = "SYM"
    VERB = "VERB"
    X = "X"


class NERLabel(str, Enum):
    """Common spaCy NER labels."""

    PERSON = "PERSON"
    NORP = "NORP"  # Nationalities, religious, political groups
    FAC = "FAC"  # Buildings, airports, highways, bridges
    ORG = "ORG"  # Companies, agencies, institutions
    GPE = "GPE"  # Countries, cities, states
    LOC = "LOC"  # Non-GPE locations, mountain ranges, bodies of water
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"
    WORK_OF_ART = "WORK_OF_ART"
    LAW = "LAW"
    LANGUAGE = "LANGUAGE"
    DATE = "DATE"
    TIME = "TIME"
    PERCENT = "PERCENT"
    MONEY = "MONEY"
    QUANTITY = "QUANTITY"
    ORDINAL = "ORDINAL"
    CARDINAL = "CARDINAL"


# ═══════════════════════════════════════════════════════════════════════════
# Linguistic Primitives
# ═══════════════════════════════════════════════════════════════════════════


class TokenAnnotation(BaseModel):
    """A single token with its full linguistic annotation."""

    index: int = Field(..., description="0-based position in the sentence")
    text: str = Field(..., description="Surface form")
    lemma: str = Field(..., description="Base/dictionary form")
    pos: str = Field(..., description="Coarse POS tag (UD)")
    tag: str = Field(..., description="Fine-grained POS tag")
    dep: str = Field(..., description="Dependency relation label")
    head: int = Field(..., description="Index of the syntactic head token")
    is_stop: bool = Field(False, description="Whether this is a stop word")
    is_alpha: bool = Field(False, description="Whether this is alphabetic")
    is_punct: bool = Field(False, description="Whether this is punctuation")
    morph: str = Field(
        "", description="Morphological features string (e.g. 'Number=Sing|Person=3')"
    )
    children: List[int] = Field(
        default_factory=list, description="Indices of dependent tokens"
    )


class NamedEntitySpan(BaseModel):
    """A named entity detected in text."""

    text: str = Field(..., description="Entity surface text")
    label: str = Field(..., description="NER label (PERSON, ORG, etc.)")
    start: int = Field(..., description="Start character offset")
    end: int = Field(..., description="End character offset")
    token_indices: List[int] = Field(
        default_factory=list, description="Token indices covered by this entity"
    )


class DependencyEdge(BaseModel):
    """A typed dependency relation between two tokens."""

    source: int = Field(..., description="Head token index")
    target: int = Field(..., description="Dependent token index")
    relation: str = Field(..., description="Dependency label (nsubj, dobj, amod, …)")


class NounChunk(BaseModel):
    """A noun phrase chunk."""

    text: str
    root_index: int
    token_indices: List[int]


# ═══════════════════════════════════════════════════════════════════════════
# Linguistic Analysis
# ═══════════════════════════════════════════════════════════════════════════


class LinguisticAnalysis(BaseModel):
    """Complete linguistic analysis of a text segment.

    This is the enriched output that the `get_tags` tool will return
    after the enhancement in Phase B.
    """

    text: str = Field(..., description="The original input text")
    tokens: List[TokenAnnotation] = Field(
        default_factory=list, description="Token-level annotations"
    )
    entities: List[NamedEntitySpan] = Field(
        default_factory=list, description="Named entities found"
    )
    dependencies: List[DependencyEdge] = Field(
        default_factory=list, description="Dependency edges"
    )
    noun_chunks: List[NounChunk] = Field(
        default_factory=list, description="Noun phrase chunks"
    )
    root_verb: Optional[str] = Field(
        None, description="Lemma of the root verb, if any"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Conversation Structure
# ═══════════════════════════════════════════════════════════════════════════


class Speaker(BaseModel):
    """A participant in a conversation."""

    id: str = Field(..., description="Unique speaker identifier")
    label: Optional[str] = Field(None, description="Display name if available")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Speaker-level metadata from corpus"
    )


class PragmaticFeatures(BaseModel):
    """Pragmatic annotations for an utterance."""

    politeness_score: Optional[float] = Field(
        None, description="Politeness probability from Convokit transformer"
    )
    toxicity_score: Optional[float] = Field(
        None, description="Toxicity score from Convokit"
    )
    is_section_header: bool = Field(
        False, description="Whether this utterance is a section header"
    )
    has_personal_attack: bool = Field(
        False, description="Whether this utterance contains a personal attack"
    )
    dialogue_act: Optional[str] = Field(
        None,
        description="Dialogue act label: question, statement, request, greeting, …",
    )


class Utterance(BaseModel):
    """A single turn in a conversation."""

    id: str = Field(..., description="Unique utterance identifier")
    speaker_id: str = Field(..., description="Speaker who produced this utterance")
    text: str = Field(..., description="Utterance text content")
    reply_to: Optional[str] = Field(
        None, description="ID of the utterance this replies to"
    )
    timestamp: Optional[float] = Field(None, description="Unix timestamp")
    linguistic_analysis: Optional[LinguisticAnalysis] = Field(
        None, description="Linguistic analysis of this utterance"
    )
    pragmatic_features: PragmaticFeatures = Field(
        default_factory=PragmaticFeatures, description="Pragmatic annotations"
    )


class Conversation(BaseModel):
    """A multi-turn conversation with structure and metadata."""

    id: str = Field(..., description="Unique conversation identifier")
    corpus: Optional[str] = Field(None, description="Source corpus name")
    utterances: List[Utterance] = Field(
        default_factory=list, description="Ordered utterance list"
    )
    speakers: List[Speaker] = Field(
        default_factory=list, description="Distinct speakers in this conversation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Conversation-level metadata"
    )
    reply_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Adjacency map: utterance_id → [reply_utterance_ids]",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Ontological Representation
# ═══════════════════════════════════════════════════════════════════════════


class OntologicalEntity(BaseModel):
    """A node in the ontology graph — an entity, concept, or feature.

    The `id` field doubles as the Obsidian wikilink target (e.g. "Professor_Entity"
    becomes [[Professor_Entity]] in markdown).
    """

    id: str = Field(
        ...,
        description="Unique entity ID; also used as the Obsidian wikilink slug",
    )
    entity_type: EntityType = Field(
        ..., description="rdf:type of this entity", alias="rdf_type"
    )
    label: str = Field(..., description="Human-readable label")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value properties (e.g. ex:hasPOSTag → VERB)",
    )
    source_utterance: Optional[str] = Field(
        None, description="Utterance ID where this entity was extracted"
    )

    class Config:
        populate_by_name = True


class Triple(BaseModel):
    """A single RDF triple.

    Subjects and objects may be entity IDs (for entities defined in the same
    analysis), full URIs, or literal values.
    """

    subject: str = Field(..., description="Subject (entity ID, URI, or blank node)")
    predicate: str = Field(..., description="Predicate (full or prefixed URI)")
    obj: str = Field(..., description="Object (entity ID, URI, or literal)", alias="object")
    subject_type: Literal["uri", "entity_id", "blank_node"] = "entity_id"
    object_type: Literal["uri", "entity_id", "literal"] = "entity_id"
    datatype: Optional[str] = Field(
        None, description="XML Schema datatype for literal objects"
    )

    class Config:
        populate_by_name = True


class OntologyGraph(BaseModel):
    """A connected set of ontological entities and their relationships.

    This is the core knowledge representation that the pipeline extracts
    from conversation text.
    """

    prefixes: Dict[str, str] = Field(
        default_factory=lambda: {
            "rdf": OntologyPrefix.RDF.value,
            "rdfs": OntologyPrefix.RDFS.value,
            "owl": OntologyPrefix.OWL.value,
            "ex": OntologyPrefix.EX.value,
            "convokit": OntologyPrefix.CONVOKIT.value,
            "nif": OntologyPrefix.NIF.value,
        },
        description="Prefix-to-namespace-URI mappings",
    )
    entities: List[OntologicalEntity] = Field(
        default_factory=list, description="All ontological entities extracted"
    )
    triples: List[Triple] = Field(
        default_factory=list, description="RDF triples connecting entities"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Obsidian Artifact
# ═══════════════════════════════════════════════════════════════════════════


class ObsidianNote(BaseModel):
    """A markdown note formatted for Obsidian with YAML frontmatter.

    The frontmatter carries the structured ontology data; the body provides
    a human-readable narrative with [[wikilinks]] connecting related concepts.
    """

    filename: str = Field(
        ..., description="Base filename (e.g. 'utterance_001.md')"
    )
    yaml_frontmatter: Dict[str, Any] = Field(
        default_factory=dict,
        description="YAML frontmatter carrying RDF type, prefixes, entity data",
    )
    body: str = Field(
        "", description="Markdown body with [[wikilinks]] and narrative sections"
    )
    wikilinks: List[str] = Field(
        default_factory=list,
        description="List of [[target]] references embedded in the body",
    )
    tags: List[str] = Field(default_factory=list, description="Obsidian tags (#tag)")


# ═══════════════════════════════════════════════════════════════════════════
# Visualization Specs
# ═══════════════════════════════════════════════════════════════════════════


class VisualizationSpec(BaseModel):
    """Metadata for a generated visualization file."""

    viz_type: Literal[
        "dep_tree", "ent_display", "semantic_network", "conversation_graph"
    ] = Field(..., description="Visualization kind")
    file_path: str = Field(..., description="Absolute or relative path on disk")
    format: str = Field("svg", description="File format: svg, html, png")
    description: str = Field("", description="What this visualization shows")


# ═══════════════════════════════════════════════════════════════════════════
# Top-Level Agent Output (the envelope the LLM is expected to produce)
# ═══════════════════════════════════════════════════════════════════════════


class OntologicalAnalysis(BaseModel):
    """**Top-level output schema** for an ontological conversation analysis.

    This is what the agent pipeline should produce as its final structured
    response.  Every field the agent cannot populate stays at its default
    (empty list / None) so the schema is usable even for partial analyses.

    Example usage inside the agent::

        result = OntologicalAnalysis(
            analysis_id="conv_001",
            source_text="Hello, Professor...",
            ontology=OntologyGraph(entities=[...], triples=[...]),
            obsidian_notes=[ObsidianNote(filename="utterance_001.md", ...)],
        )
        return result.model_dump_json(indent=2)
    """

    # ── Bookkeeping ──────────────────────────────────────────────────────
    analysis_id: str = Field(
        ..., description="Unique identifier for this analysis run"
    )
    source_text: str = Field(
        ..., description="The original text or conversation that was analyzed"
    )
    source_corpus: Optional[str] = Field(
        None, description="Source corpus name when loaded from Convokit"
    )

    # ── Linguistic layer ─────────────────────────────────────────────────
    linguistic_analysis: Optional[LinguisticAnalysis] = Field(
        None, description="Per-utterance or whole-text linguistic annotation"
    )

    # ── Conversation layer ───────────────────────────────────────────────
    conversation: Optional[Conversation] = Field(
        None, description="Multi-turn conversation structure when applicable"
    )

    # ── Ontological layer ────────────────────────────────────────────────
    ontology: OntologyGraph = Field(
        default_factory=OntologyGraph,
        description="Entities, triples, and prefix definitions",
    )

    # ── Artifacts ────────────────────────────────────────────────────────
    obsidian_notes: List[ObsidianNote] = Field(
        default_factory=list,
        description="Obsidian .md files generated for graph browsing",
    )
    visualizations: List[VisualizationSpec] = Field(
        default_factory=list, description="Rendered visualizations produced"
    )

    # ── Narrative ────────────────────────────────────────────────────────
    summary: str = Field(
        "", description="Human-readable synthesis of the ontological findings"
    )
