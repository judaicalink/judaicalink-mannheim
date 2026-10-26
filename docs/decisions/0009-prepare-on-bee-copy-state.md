# 0009 New data is loaded on the test VM on bee and its state copied to mannheim

Status: accepted · Date: 2026-10-26 · Amends [0001](0001-platform.md)

## Context

A reload (`services/load.sh`: the database over HTTP, the check, the search index, the dashboard) and the jobs of
the showcases take 2 to 3 hours on mannheim, whose disk is slow: on 2026-10-26 the search index alone took 40
minutes there and 6 on a test VM. Every change also has to run on a test VM first, and both should end identical.
bee, in the university network, runs the test VM and reaches mannheim at about 107 MB/s.

## Decision

- New data is loaded, indexed and checked on the test VM on bee (the same steps as before: `services/load.sh`, the
  jobs of the showcases with a server, the checks).
- `host/copy-state.sh <target>`, run on that VM, copies its state to mannheim: the database the endpoint uses, the
  Solr home with all cores, the generated pages (figures, dashboard, `status.json`), the store (`/dumps`) and the data
  of the showcases (`/data/mannheim/showcases`). It requires the same commits of this repository and of the showcase
  repositories on both VMs; it stops Solr, the graph application and the showcase containers on the target while their
  files are replaced, switches the endpoint to the copied database, and accepts the copy when the target counts the
  same triples. `--dry-run` shows what would be copied.
- Files keep the owner the target directory has (user ids differ between the VMs), except Solr's, which belong to the
  container user with the same id everywhere.
- The static showcases and the site are copied as before with `host/deploy.sh`. `load.sh` on mannheim stays possible
  (e.g. when bee is not available).
- Old databases are removed by hand on both VMs, as before.

## Consequences

mannheim is busy for minutes instead of hours, and has exactly the state that was checked on the test VM. The copy
moves up to about 40 GB (the database is not compacted while the files have numbers of 19 or more digits).
