# Decisions about mannheim.judaicalink.org

One file per decision, numbered. Status `proposed` until agreed, then `accepted`. Decisions about the data (catalogue,
generation, dumps, entity pages) are in [judaicalink-data](https://github.com/judaicalink/judaicalink-data/tree/main/docs/decisions).

| | Decision | Date |
|---|---|---|
| [0001](0001-platform.md) | The platform: static site (Hugo, nginx), central services in Docker Compose (Fuseki read-only, Solr when needed), one repository per showcase; proposed | 2026-10-13 |
| [0002](0002-iris-sparql-platform-bar.md) | The view of a JudaicaLink IRI is the IRI with the host swapped (data, datasets, ontology terms), one resource view; `/sparql` endpoint and `/sparql/` editor, every number links to its query; one platform bar for all showcases, put in by nginx (SSI); ontology section proposed | 2026-10-14 |
| [0003](0003-graph-application.md) | One platform application (`apps/graph`) for IRI views and graph search; its jobs (figures, index, dashboard) run after each load; an internal Fuseki service without time limit | 2026-10-14 |
| [0004](0004-solr-central.md) | Solr 9 as a central service; each application creates and owns its cores over the API, rebuilds are swapped in | 2026-10-14 |
| [0005](0005-graph-search.md) | Graph search: entity pages by default, other datasets by choice or all, facets (kind, occupation, place of birth, century) | 2026-10-14 |
| [0006](0006-graph-dashboard.md) | The graph dashboard is part of the platform (`/dashboard/`); Compact Memory has its own in its showcase | 2026-10-14 |
| [0007](0007-showcase-contract.md) | The showcase contract: registry fields `datasets` and `resolve`, a data folder per showcase, services, reserved paths | 2026-10-14 |
| [0008](0008-feedback.md) | Feedback on the data: a button in the platform bar opens a panel (explanation, selected text, resource of the page) that prepares an issue in judaicalink-data or gives the text to copy | 2026-10-26 |
| [0009](0009-prepare-on-bee-copy-state.md) | New data is loaded and checked on the test VM on bee; `host/copy-state.sh` copies the state (database, Solr, generated pages, store, showcase data) to mannheim | 2026-10-26 |
