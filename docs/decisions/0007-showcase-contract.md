# 0007 The showcase contract: registry, data folder, links between showcases and the platform

Status: accepted (made autonomously on 2026-10-14; to be reviewed) · Date: 2026-10-14 · Amends [0001](0001-platform.md)

## Context

With two showcases built at the same time in their own repositories (jlma-haskala, jlma-compact-memory), what a showcase
may expect from the platform, and what it gives back, needed to be fixed.

## Decision

- **Registry** (`site/data/showcases.toml`): `path`, `title`, `description`, `port` (only with a server),
  `repository`, `publication`; new, optional: `datasets` (the JudaicaLink datasets the showcase presents) and
  `resolve` (a URL template with `{iri}`, e.g. `/compact-memory/resolve?iri={iri}`). The platform's views link a
  record of one of these datasets to the showcase with the record's IRI, and an entity page whose sources are in them
  with the entity page's IRI ("In the showcases"): the showcase decides which of its records it shows for an entity
  page (it may know several, e.g. a person of haskala-library.net and of haskala.net). A showcase's resolve therefore
  understands entity page IRIs (`…/data/ep/<n>`) too.
- **Data folder**: `/data/mannheim/showcases/<path>/` (owned by the deploy user) holds a showcase's inputs, caches and
  generated files; inputs that are not public (e.g. the Compact Memory full text) stay there and in no repository.
- **Services** on the Docker network `judaicalink`: `http://fuseki:3030/internal/query` (or `/judaicalink/query`),
  `http://solr:8983/solr` (own cores, 0004); the files of the loaded versions in `/data/mannheim/store` (read only).
- **Links**: JudaicaLink IRIs are linked by the rule of 0002; a showcase does not build its own generic entity pages.
- Reserved paths: `sparql`, `dumps`, `showcases`, `data`, `datasets`, `ontology`, `search`, `dashboard`, `kit`, `about`,
  `status.json` (and the site's asset folders).
