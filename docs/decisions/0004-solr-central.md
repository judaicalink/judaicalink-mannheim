# 0004 Solr is a central service; each application owns its cores

Status: accepted (made autonomously on 2026-10-14; to be reviewed) · Date: 2026-10-14 · Amends [0001](0001-platform.md)

## Context

0001 planned Solr "when a showcase needs it", with the major version of Frankfurt. Now the graph search (platform) and
the Compact Memory showcase need full text. Frankfurt's Solr version is not recorded anywhere in the portal
repository (it runs outside their Compose setup); their full-text bundle was tested against Solr 9.

## Decision

- One Solr (official image `solr:9.10.1`, standalone, heap `SOLR_HEAP`, data in `/data/mannheim/solr`) in
  `services/compose.yml`, on the Docker network as `http://solr:8983/solr` and on 127.0.0.1:8983; never public.
- **Each application owns its cores.** A core is made with `solr create -c <name> -d _default` inside the Solr
  container (`services/solr-core.sh` for the platform; showcases do the same from their own scripts), which copies the
  configset into the core. Fields are then defined with the Schema API, guessing of fields switched off
  (`update.autoCreateFields=false`). Not over CoreAdmin with `configSet=_default`: in standalone Solr such cores *share*
  the configset, so one application's fields would end up in every other core (found by the Compact Memory showcase,
  2026-10-14). Solr puts a fresh copy of `_default` into its home at every start. Core names start with the owner
  (`graph`, `cm_…`).
- A rebuild goes into a new, uniquely named core (`graph_<timestamp>`), which is then swapped in under the name the
  application searches (CoreAdmin `SWAP`, or `RENAME` the first time), so searches never see a half-built index.

## Consequences

- When Frankfurt's version is known, the image follows its major version if that differs.
- `apps/graph/solr.py` is the small client the platform uses; showcases keep their own copy (no shared code between
  repositories).
