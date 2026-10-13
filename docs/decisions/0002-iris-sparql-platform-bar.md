# 0002 mannheim.judaicalink.org: one view per IRI by swapping the host; SPARQL; one platform bar

Status: accepted (2026-10-14); the section "Ontology terms" is proposed · Date: 2026-10-14 · Builds on
[0001](0001-platform.md); amends judaicalink-data [0001](https://github.com/judaicalink/judaicalink-data/blob/main/docs/decisions/0001-roles-and-hosts.md) (pubby-like frontend)

## Context

The showcases of mannheim.judaicalink.org live in repositories of their own (0001). For them to form one site, the
same entity must lead to the same page wherever it appears, and every number must be checkable. Until now each
demonstrator rendered entities itself (the entity-page demonstrator under `/entities/ep/<id>`), and judaicalink-data 0001 left open
whether a pubby-like frontend is needed. In Frankfurt, `data.judaicalink.org` resolves data IRIs, but not the terms of
the ontology (`data.judaicalink.org/ontology/birthDate` ends on a 404 page of the portal, also for Turtle).

## Decision

### IRIs

- **The Mannheim view of a JudaicaLink IRI is the same IRI with the host replaced:**
  `http://data.judaicalink.org/<path>` → `https://mannheim.judaicalink.org/<path>`, for data
  (`/data/<namespace>/<id>`), datasets (`/datasets/<slug>`) and ontology terms (`/ontology/<term>`). No prefix, nothing
  else to remember. IRIs keep being coined in `data.judaicalink.org` (judaicalink-data 0002); the swap is only for links.
- **Showcases link every JudaicaLink IRI this way** and do not build their own entity views.
- **One resource view in the platform** answers these paths: entity pages (`/data/ep/…`) with their sources and history
  (redirects for merged pages, the list for split ones, as in judaicalink-data 0022), any other record with its triples, a dataset with
  its `-meta` description and a link to the catalogue on web.judaicalink.org. Every JudaicaLink IRI on a page is linked
  by the same rule; IRIs of other vocabularies and authorities link to themselves. With `Accept: text/turtle` (or
  N-Triples, JSON-LD) the view returns the triples of the IRI instead of HTML.

### SPARQL

- **`/sparql`** is the endpoint (read-only Fuseki, 0001); **`/sparql/`** is the query editor (a static page) on it.
- Every number or table that a showcase or the resource view shows from the graph links to its query in the editor
  (`/sparql/?query=…`).

### One platform bar, loaded live (agreed 2026-10-14)

- Every page of the platform and of every showcase carries the same bar (brand, showcases, SPARQL, data, project,
  the link to production in Frankfurt). Showcases load it live, not a copy: a showcase page contains
  `<!--# include virtual="/kit/1/header.html" -->` and nginx puts the bar in (server-side includes). It is part of
  the HTML as delivered: no JavaScript, no delay, readable for search engines; outside the platform it is a comment.
- The bar is built by the Hugo site from the showcase registry; `/kit/1/jl.css` holds the common look. Kit 1 only
  gets compatible changes; a breaking change becomes kit 2.
- The resource views point search engines to the page of the same IRI in Frankfurt (`<link rel="canonical">`), so
  that searches lead to production; showcases are indexed as themselves.

### Ontology terms (proposed)

- `/ontology/<term>` (from the rule above) shows the term as defined in the loaded version of the ontology (label,
  comment, domain, range, the class it is documented under), how the graph uses it (triples per dataset, examples),
  and links to its section on ontology.judaicalink.org (`#jl<term>`), which stays the documentation of the ontology.
  `/ontology/` lists all terms with their use, and the terms the data uses that the ontology does not define.
- The use of the terms is computed once when the graph is loaded (the query over the whole graph takes about 80 s),
  together with the other figures of the loaded graph (`/status.json`).

## Consequences

- The entity views of the ep-demonstrator move into the resource view; the demonstrator keeps its search and becomes
  the target of the platform's search box. Its paths `/entities/ep/<id>` redirect to `/data/ep/<id>`.
- Paths reserved on the platform: `data`, `datasets`, `ontology`, `sparql`, `dumps`, `kit`, `status.json`.
- Found on 2026-10-14: rujen uses `jl:Person` as a class (8,283 records), which the ontology does not define.
