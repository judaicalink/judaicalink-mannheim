# 0004 Solr is a central service; each application owns its cores

Status: accepted (made autonomously on 2026-10-14; to be reviewed) · Date: 2026-10-14 · Amends [0001](0001-platform.md)

## Context

0001 planned Solr "when a showcase needs it", with the major version of Frankfurt. Now the graph search (platform) and
the Compact Memory showcase need full text. Frankfurt's Solr version is not recorded anywhere in the portal
repository (it runs outside their Compose setup); their full-text bundle was tested against Solr 9.

## Decision

- One Solr (official image `solr:9.10.1`, standalone, heap `SOLR_HEAP`, data in `/data/mannheim/solr`) in
  `services/compose.yml`, on the Docker network as `http://solr:8983/solr` and on 127.0.0.1:8983; never public.
- **Each application owns its cores** and makes them itself over the API: CoreAdmin `CREATE` from the `_default`
  configset, fields with the Schema API, guessing of fields switched off (`update.autoCreateFields=false`). No
  configset files on the server, nothing to copy by hand. Core names start with the owner (`graph`, `cm_…`).
- A rebuild goes into `<core>_new` and is swapped in (CoreAdmin `SWAP`), so searches never see a half-built index.

## Consequences

- When Frankfurt's version is known, the image follows its major version if that differs.
- `apps/graph/solr.py` is the small client the platform uses; showcases keep their own copy (no shared code between
  repositories).
