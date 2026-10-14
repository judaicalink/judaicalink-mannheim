---
title: Data
description: The Mannheim version of the JudaicaLink knowledge graph, its SPARQL endpoint and files.
---

This platform holds the current Mannheim version of the JudaicaLink knowledge graph. It is reloaded when new
versions of the data are published, so results can change. Production runs in Frankfurt, which can have another
state of the data.

- **SPARQL editor:** [/sparql/](/sparql/). The endpoint for programs is `https://mannheim.judaicalink.org/sparql`
  (read-only, GET or POST; queries stop after 120 seconds).
- **What is loaded:** the stable version of every dataset of the catalogue that is not replaced by another, with the
  corrections applied. Each dataset is a named graph, `http://data.judaicalink.org/datasets/<slug>`; its description
  (VoID, DCAT, PROV) is in `…/<slug>/meta`. A query without `GRAPH` sees all graphs together.
- **Files:** [/dumps/](/dumps/), the files of the loaded versions in the layout `<slug>/<version>/<path>`.
- **Every IRI** of JudaicaLink has its view here, at the same path: `http://data.judaicalink.org/data/ep/1007316` is
  [/data/ep/1007316](/data/ep/1007316), `…/datasets/bhr` is [/datasets/bhr](/datasets/bhr), `…/ontology/birthDate` is
  [/ontology/birthDate](/ontology/birthDate). Ask for `text/turtle`, `application/n-triples` or
  `application/ld+json` (or add `.ttl`, `.nt`, `.jsonld`) to get the data. Search engines are pointed to the pages in
  production (data.judaicalink.org).
- **Search and figures:** the [graph search](/search/), the [dashboard](/dashboard/), the [datasets](/datasets/) and
  the [ontology](/ontology/) with the use of each term; `/status.json` says what is loaded.
- **Catalogue:** the datasets with all their versions, files and sources are described in the
  [catalogue on web.judaicalink.org](https://web.judaicalink.org/datasets/).
