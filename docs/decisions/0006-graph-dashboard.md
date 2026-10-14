# 0006 The graph dashboard is part of the platform; Compact Memory has its own

Status: accepted (made autonomously on 2026-10-14; to be reviewed) · Date: 2026-10-14

## Context

The workspace dashboard (`dashboard/`) showed Compact Memory and the knowledge graph together, made from QLever and
the full-text bundle, published as a claude.ai artifact. Kai: the graph dashboard belongs to the central platform, a
Compact Memory dashboard to the Compact Memory showcase (2026-10-14).

## Decision

- `/dashboard/` is the graph dashboard: the knowledge-graph view of the old dashboard, made by `jobs.py dashboard` from
  Fuseki after every load (static HTML with the data embedded, the platform bar and the kit look), every figure linked
  to its query in the SPARQL editor.
- The Compact Memory view moves to the showcase jlma-compact-memory (`/compact-memory/dashboard/`).
- Public figures follow the framing agreed for statistics: the whole graph as it grows, no before/after comparisons.
