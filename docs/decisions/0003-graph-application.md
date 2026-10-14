# 0003 One platform application for IRI views and graph search; its jobs run after each load

Status: accepted (made autonomously on 2026-10-14 while Kai was away; to be reviewed) · Date: 2026-10-14 · Builds on
[0002](0002-iris-sparql-platform-bar.md)

## Context

0002 asked for one resource view for every JudaicaLink IRI, and Kai asked for a graph search and a graph dashboard as
parts of the central platform (2026-10-14). The ep-demonstrator (workspace `ep-demonstrator/`) already rendered entity
pages, with an in-memory search index that took a minute to build at every start.

## Decision

- **One application, `apps/graph/`** (standard library, one container `graph`, 127.0.0.1:8090), answers
  `/data/…`, `/datasets/…`, `/ontology/…` (the views of 0002) and `/search/` (the graph search,
  [0005](0005-graph-search.md)). It renders HTML with the kit and the platform bar, and Turtle, N-Triples or JSON-LD
  for any IRI (by `Accept` or by the suffix `.ttl`, `.nt`, `.jsonld`), made by Fuseki.
- Entity pages follow decision 0022 of judaicalink-data: a merged page answers 301 to the page it was merged into, a
  split page 300 with its parts, a retired page 410; each shows its sources (the records it represents, with the
  statements of every dataset), identifiers grouped by authority, and its history (pages merged into it).
- Every view points search engines to the page of the same IRI in production (`rel=canonical`, 0002).
- **Jobs in the same image** (`docker compose run --rm graph python3 jobs.py stats|index|dashboard|all`) compute what
  is too slow for a request: the figures of the loaded graph (`/status.json`, figures per dataset, use of the ontology
  terms), the search index and the graph dashboard ([0006](0006-graph-dashboard.md)). They write to
  `/data/mannheim/www/generated/`, which nginx serves (`/status.json`, `/dashboard/`) and the application reads.
- **Fuseki gets a second service on the same data, `internal`**, without the time limit of the public one, for the
  jobs and for showcase containers; it is reachable only on 127.0.0.1 and the Docker network. The time limit of the
  public service is set per endpoint (Fuseki ignores it per service).

## Consequences

- The ep-demonstrator is replaced: its entity views are here, its search is the graph search.
- `services/load.sh` runs the jobs after switching to a new database.
