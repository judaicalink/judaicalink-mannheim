# Decisions about mannheim.judaicalink.org

One file per decision, numbered. Status `proposed` until agreed, then `accepted`. Decisions about the data (catalogue,
generation, dumps, entity pages) are in [judaicalink-data](https://github.com/judaicalink/judaicalink-data/tree/main/docs/decisions).

| | Decision | Date |
|---|---|---|
| [0001](0001-platform.md) | The platform: static site (Hugo, nginx), central services in Docker Compose (Fuseki read-only, Solr when needed), one repository per showcase; proposed | 2026-10-13 |
| [0002](0002-iris-sparql-platform-bar.md) | The view of a JudaicaLink IRI is the IRI with the host swapped (data, datasets, ontology terms), one resource view; `/sparql` endpoint and `/sparql/` editor, every number links to its query; one platform bar for all showcases, put in by nginx (SSI); ontology section proposed | 2026-10-14 |
