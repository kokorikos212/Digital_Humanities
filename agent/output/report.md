# Linguistic Analysis Report

**Phrase:** *The quick brown fox jumps over the lazy dog*

---

## 1. Tokenization

| Token  | POS Tag | Label         |
|--------|---------|---------------|
| The    | DET     | Determiner    |
| quick  | ADJ     | Adjective     |
| brown  | ADJ     | Adjective     |
| fox    | NOUN    | Noun          |
| jumps  | VERB    | Verb          |
| over   | ADP     | Adposition    |
| the    | DET     | Determiner    |
| lazy   | ADJ     | Adjective     |
| dog    | NOUN    | Noun          |

---

## 2. Part-of-Speech Summary

- **Determiners (DET):** 2 — "The", "the"
- **Adjectives (ADJ):** 3 — "quick", "brown", "lazy"
- **Nouns (NOUN):** 2 — "fox", "dog"
- **Verbs (VERB):** 1 — "jumps"
- **Adpositions (ADP):** 1 — "over"

---

## 3. Named Entity Recognition

No named entities (persons, locations, organizations, etc.) were detected. All tokens are common English words.

---

## 4. Syntactic Structure

The phrase forms a simple **Subject–Verb–Prepositional Phrase** structure:

- **Subject:** "The quick brown fox"  
  *(DET + ADJ + ADJ + NOUN)*
- **Verb:** "jumps"  
- **Prepositional Phrase:** "over the lazy dog"  
  *(ADP + DET + ADJ + NOUN)*

The head noun of the subject is **"fox"**, modified by the adjectives *quick* and *brown*.  
The head noun of the prepositional object is **"dog"**, modified by the adjective *lazy*.

---

## 5. Visualization

- **Dependency Syntax Tree:** `output/graphs/viz_dep_1778106882.svg`
- **Entity Visualization:** `output/graphs/viz_ent_1778106882.svg`

---

## 6. Notable Observations

- This phrase is a **pangram** — it contains every letter of the English alphabet at least once. It is famously used for typography and font display.
- Despite its fame, the sentence yields **zero named entities**.
- The structure is grammatically canonical: *determiner → adjectives → noun → verb → preposition → determiner → adjective → noun*.

---

*Report generated via Linguistic Ontology Toolkit.*
