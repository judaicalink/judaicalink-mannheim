# 0010 haskala-library.net redirects to the Library of Haskala showcase

Status: accepted · Date: 2026-11-03

## Context

The Library of Haskala was published at haskala-library.net (Drupal, 2015–2025). The site is offline; the
showcase `/haskala/` shows the same records at the old paths (jlma-haskala decision 0002). Old links, citations
and the dataset (`jl:describedAt`) use the old addresses. Since 2026-11 haskala-library.net and
www.haskala-library.net point to mannheim.judaicalink.org.

## Decision

- Both names redirect permanently (301) to `https://mannheim.judaicalink.org/haskala/<old path>/`, over http and
  https; the query of an old address is dropped. `alignment of text/…` (no-break spaces) goes to
  `alignment-of-text/…`; an address that is not a plain path goes to the start page of the showcase.
- The domain is not a second home of the showcase: its pages are served only below mannheim.judaicalink.org.
- `host/nginx/haskala-library.net.conf`, installed by `host/install.sh` with a Let's Encrypt certificate of its
  own (`haskala-library.net`, both names; renewed by the certbot timer), self-signed on a test VM.

## Consequences

- An old address without a page in the showcase (`/content/…`, files of the Drupal site) ends in a 404 there.
- A certificate of its own keeps the certificate of mannheim.judaicalink.org independent of the domain.
