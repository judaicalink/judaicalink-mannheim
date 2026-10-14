# 0005 The graph search: entity pages by default, other datasets by choice, facets

Status: accepted (made autonomously on 2026-10-14; to be reviewed) · Date: 2026-10-14

## Context

Kai: the graph search shows only entity pages by default; the visitor can choose other datasets, several, or a full
graph search with facets (2026-10-14).

## Decision

- **One Solr core `graph`, one document per labelled IRI** of every dataset graph (made by `jobs.py index` from the
  internal SPARQL service): labels and alternative names (prefix-indexed for suggestions, folded for diacritics),
  abstract, the datasets that make statements about it, classes and a broad kind (person, place, work,
  organisation, subject …), birth and death as recorded, birth year and century, place of birth and occupations
  (labels resolved), the entity page that represents a record, the status of an entity page.
- Left out: subjects that are not looked for by name and that the showcases present (Compact Memory pages and
  issues, TagMe mentions, corpus presence), and blank nodes.
- **Default: entity pages that are in use** (not merged, split or retired). A list of datasets with counts lets the
  visitor choose one or several, or "all datasets"; the counts stay visible while filtering (Solr tag/exclude).
- Facets: kind, occupation, place of birth, century. Ranking: edismax over labels, alternative names and abstract;
  entity pages with more sources rank higher.
- `/search/suggest?q=…&ds=…` returns JSON for autocompletion (also for showcases; CORS open).
