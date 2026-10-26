# 0008 Feedback on the data: a panel in the platform bar that prepares a GitHub issue

Status: accepted · Date: 2026-10-26 · Amends [0007](0007-showcase-contract.md)

## Context

Data is shown in many places: the views of every IRI, the graph search, the dashboard, the showcases, the catalogue
on web.judaicalink.org. Feedback on it should be possible from all of them in the same way, and it should be public,
so that others can follow it and the corrections are traceable (judaicalink-data fixes data in the data, decision
0024 there).

## Decision

- **A Feedback button in the platform bar** (`/kit/1/header.html`), so every page that includes the bar (SSI) has it,
  every showcase included, without changes of its own. The script `/kit/1/feedback.js` and `/kit/1/feedback.css`
  come with the bar; any element with `data-jl-feedback` opens the panel.
- **Two steps:** the panel first explains how feedback works (select the text on the page, describe what is wrong,
  open the prepared issue or copy the text); then a form: the resource it is about, the selected text (taken from
  what the visitor selects while the panel is open), the feedback, the subject, the page.
- **The resource** is found on the page: the element with `data-jl-iri` around the selected text; else
  `<meta name="jl:subject">`; else the `?iri=` of the address (the resolve links of the showcases); else the canonical
  link (the IRI views link Frankfurt's page of the IRI); else the path of a platform view (`/data/…`, `/datasets/…`)
  or a dataset page of web.judaicalink.org. Showcases may mark their elements with `data-jl-iri`; they need not.
- **The issue** goes to the public tracker of judaicalink-data on GitHub, through the issue form
  `.github/ISSUE_TEMPLATE/feedback.yml` there (label `feedback`), its fields filled by the link. Feedback about a
  showcase rather than the data is moved to the showcase's repository there.
- **Without a GitHub account:** the whole text (subject and body) can be copied, to send it to the team (the team page
  of web.judaicalink.org) or to keep it. No e-mail address in the panel.
- **Nothing is sent by the platform:** the script builds a link and a text; the visitor submits the issue on GitHub.
  The draft is kept in the browser's session storage for the page, so that closing the panel loses nothing. No form
  on the platform takes input (0001: read-only).
- web.judaicalink.org has a copy of the same script and styles (its pages are not served by the platform).
