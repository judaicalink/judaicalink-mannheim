# 0001 mannheim.judaicalink.org: a static site, central services in Docker, one repository per showcase

Status: proposed · Date: 2026-10-13 · Amends judaicalink-data [0001](https://github.com/judaicalink/judaicalink-data/blob/main/docs/decisions/0001-roles-and-hosts.md) (consequences) and
judaicalink-data [0016](https://github.com/judaicalink/judaicalink-data/blob/main/docs/decisions/0016-data-access-outside.md) (where the platform code lives)

## Context

judaicalink-data [0001](https://github.com/judaicalink/judaicalink-data/blob/main/docs/decisions/0001-roles-and-hosts.md) made mannheim.judaicalink.org the Mannheim platform: our version of the graph
(SPARQL), our dumps, demonstrators. The former labs portal was a Django application; the platform is not a
production service and will not always be maintained, so it should be light and offer little to attack. Showcases
also accompany research publications, which cite them for years. Frankfurt runs Fuseki and Solr. A fresh VM
(Ubuntu 24.04) is provided for the platform, so nothing depends on the grown setup of the old VM.

The SPARQL engines were compared on the same data (2026-10-13, 40 graphs, 21.2 M triples; `../endpoints/`):
- **Fuseki 6.2.0 (TDB2)** keeps every value: strings, dates, IRIs exactly, numbers and booleans in their canonical
  form (`1.50`→`1.5`, a 16-digit `xsd:float` → its 32-bit value); 37 of 40 graphs come back identical; it accepts
  ill-typed literals. Its bulk loader `tdb2.tdbloader` wraps integers beyond 64 bits (loading over HTTP does not).
  Queries over the whole graph take 3–25 s.
- **QLever 0.6.0** changes values (decimals rounded to 13 digits, xsd:integer → xsd:int, dateTime to milliseconds;
  31 of 40 graphs identical) and aborts the whole build on one ill-typed or overlong literal; it answers in
  milliseconds.

## Decision

- **Static first.** The site is a Hugo site served by nginx; no Django, no logins, no database written by visitors.
  A showcase is static wherever possible (results computed ahead). A showcase for a publication keeps a frozen copy
  of its results and names the data versions it used.
- **One repository for the platform** (`judaicalink-mannheim`): host setup, nginx, the central services, the site
  and the registry of showcases. **One repository per showcase.** The platform knows a showcase only by its registry
  entry (path, title, description, `port` if it has a server).
- **Docker Compose** for the central services and for showcases with a server: each brings its own runtime, can be
  added or removed without touching the others, and still builds years later. Containers publish only on
  127.0.0.1; nginx on the host is the only public entry. No Swarm, no Kubernetes.
- **Fuseki is the public SPARQL endpoint** (`/sparql`, read-only, queries stop after 120 s). It holds the stable
  version of every dataset not replaced, from the data index, with the corrections applied (judaicalink-data 0018, 0023). Databases
  are built over HTTP in a separate loader container, checked against the `-meta` counts, then switched in.
  QLever stays a tool for analysis, not a public service.
- **Solr** is added when a showcase needs full text, with the major version and schema conventions of Frankfurt.
- The platform serves the files of the loaded versions as a dumps location (`/dumps/`, judaicalink-data 0019). The dataset
  catalogue stays on web.judaicalink.org (judaicalink-data 0014); the platform links to it.

## Consequences

- The workspace directories `ep-demonstrator/` and `dashboard/` become showcase repositories; `qlever/` and
  `endpoints/` stay tools of the workspace (judaicalink-data 0016).
- Whether mannheim.judaicalink.org is listed as a dumps location in `catalog/locations.toml` is decided when it
  serves files.
- The old VM is retired after its backup (workspace `BACKUP-PLAN-2026-10-10.md`); its name stays out of everything public.
- The decisions about the platform are kept here, in judaicalink-mannheim; judaicalink-data keeps those about the data.
