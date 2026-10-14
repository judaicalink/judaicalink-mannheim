"""The graph search (/search/): Solr core `graph`, built by jobs.py index. By default it searches the entity pages
(dataset ep); the visitor can choose other datasets, several, or all, and narrow down with facets."""

import json
import math
import urllib.parse

import solr
from common import esc, href, page, generated, local

CORE = "graph"
PER_PAGE = 20
FACETS = [("class", "Kind"), ("occupation", "Occupation"), ("birth_place", "Place of birth"), ("century", "Century")]


def _params(qs):
    q = (qs.get("q", [""])[0] or "").strip()[:300]
    ds = [d for d in qs.get("ds", []) if d]
    if not ds:
        ds = ["ep"]
    if "all" in ds:
        ds = []
    filters = {f: qs.get(f, []) for f, _ in FACETS}
    try:
        start = max(0, int(qs.get("start", ["0"])[0]))
    except ValueError:
        start = 0
    return q, ds, filters, start


def _solr_query(q, ds, filters, start, rows=PER_PAGE):
    fq = []
    if ds:
        fq.append("{!tag=ds}dataset:(" + " OR ".join(json.dumps(d) for d in ds) + ")")
    if not ds or ds == ["ep"]:
        fq.append("-ep_status:(merged OR split OR retired)")
    for f, vals in filters.items():
        for v in vals:
            fq.append(f"{{!tag={f}}}{f}:{json.dumps(v)}")
    params = {
        "q": q or "*:*", "defType": "edismax", "q.op": "AND",
        "qf": "label^4 label_folded^3 alt^2 alt_folded^1.5 text^0.3", "pf": "label^8",
        "bq": "dataset:ep^2", "boost": "log(sum(sources,2))",
        "fq": fq, "start": start, "rows": rows,
        "fl": "id,pref,classes,class,dataset,birth,death,birth_place,occupation,abstract,ep,ep_status,sources",
        "facet": "true", "facet.mincount": 1, "facet.limit": 15,
        "facet.field": ["{!ex=ds}dataset"] + [f"{{!ex={f}}}{f}" for f, _ in FACETS],
        "hl": "true" if q else "false", "hl.fl": "abstract", "hl.snippets": 1, "hl.fragsize": 220,
        "hl.simple.pre": "<mark>", "hl.simple.post": "</mark>",
    }
    if not q:
        params["sort"] = "sources desc, pref_sort asc"
    return solr.select(CORE, params)


def suggest(qs):
    """JSON for autocompletion: [{iri, label, kind, dates, dataset}] (also for showcases)."""
    q = (qs.get("q", [""])[0] or "").strip()[:100]
    ds = [d for d in qs.get("ds", []) if d] or ["ep"]
    if not q:
        return []
    fq = [] if "all" in ds else ["dataset:(" + " OR ".join(json.dumps(d) for d in ds) + ")"]
    if ds == ["ep"]:
        fq.append("-ep_status:(merged OR split OR retired)")
    res = solr.select(CORE, {"q": q, "defType": "edismax", "qf": "label_prefix label^2 alt_prefix^0.5",
                             "q.op": "AND", "fq": fq, "rows": min(20, int(qs.get("limit", ["10"])[0] or 10)),
                             "fl": "id,pref,class,birth,death,dataset", "boost": "log(sum(sources,2))"})
    return [{"iri": d["id"], "label": d.get("pref", ""), "kind": (d.get("class") or [""])[0],
             "dates": _dates(d), "dataset": (d.get("dataset") or [""])[0]} for d in res["response"]["docs"]]


def _dates(d):
    b, e = d.get("birth"), d.get("death")
    if b or e:
        return f"{b or '?'}–{e or ''}"
    return ""


def _url(q, ds, filters, start=0, **change):
    p = {"q": q, "ds": ds or ["all"], **{f: v for f, v in filters.items()}, "start": start}
    p.update(change)
    p = {k: v for k, v in p.items() if v not in ("", [], 0, None)}
    return "/search/?" + urllib.parse.urlencode(p, doseq=True)


def view(qs):
    q, ds, filters, start = _params(qs)
    stats = generated("graph-stats.json", {}) or {}
    try:
        res = _solr_query(q, ds, filters, start)
    except Exception as e:      # the index is built after the first load
        body = f'<h1>Graph search</h1><p class="jl-note">The search index is not available yet ({esc(type(e).__name__)}).</p>'
        return page("Graph search", body)
    n = res["response"]["numFound"]
    facets = res.get("facet_counts", {}).get("facet_fields", {})
    hl = res.get("highlighting", {})
    titles = (stats.get("titles") or {})

    # the datasets to search: entity pages (default), some, or all
    ds_counts = facets.get("dataset", [])
    pairs = sorted(zip(ds_counts[::2], ds_counts[1::2]), key=lambda x: (x[0] != "ep", -x[1]))
    boxes = []
    for d, c in pairs:
        checked = " checked" if (d in ds) else ""
        name = "Entity pages" if d == "ep" else titles.get(d, d)
        boxes.append(f'<label class="gs-ds"><input type="checkbox" name="ds" value="{esc(d)}"{checked}> '
                     f'<span dir="auto">{esc(name)}</span> <span class="jl-meta">{c:,}</span></label>')
    all_checked = " checked" if not ds else ""

    hidden = "".join(f'<input type="hidden" name="{esc(f)}" value="{esc(v)}">' for f, vals in filters.items() for v in vals)
    form = f"""<form class="gs-form" action="/search/" method="get">
  <div class="gs-bar"><input type="search" name="q" value="{esc(q)}" placeholder="Names, titles, places …" aria-label="Search" autofocus>
  <button class="jl-button" type="submit">Search</button></div>
  <details class="gs-datasets"{' open' if ds != ['ep'] else ''}><summary>Searching: {esc('all datasets' if not ds else ', '.join('entity pages' if d == 'ep' else d for d in ds))}</summary>
  <label class="gs-ds gs-all"><input type="checkbox" name="ds" value="all"{all_checked}> <strong>All datasets (the whole graph)</strong></label>
  <div class="gs-dslist">{''.join(boxes)}</div>
  <p class="jl-meta">Entity pages bring the records of all sources about one person, place or work together. Choose
  other datasets to search their records as they are.</p><button class="jl-button" type="submit">Apply</button></details>
  {hidden}
</form>"""

    # facets
    side = []
    for f, head in FACETS:
        vals = facets.get(f, [])
        if not vals:
            continue
        items = []
        for v, c in zip(vals[::2], vals[1::2]):
            on = v in filters[f]
            nf = {k: list(x) for k, x in filters.items()}
            nf[f] = [x for x in nf[f] if x != v] if on else nf[f] + [v]
            shown = local(v) if f == "class" else v
            items.append(f'<li{" class=gs-on" if on else ""}><a href="{esc(_url(q, ds, nf))}">'
                         f'<span dir="auto">{esc(shown)}</span> <span class="jl-meta">{c:,}</span></a></li>')
        side.append(f'<h3>{esc(head)}</h3><ul class="gs-facet">{"".join(items)}</ul>')

    # results
    out = []
    for d in res["response"]["docs"]:
        iri = d["id"]
        kind = ", ".join(local(c) for c in d.get("class", [])[:2])
        meta = " · ".join(x for x in [kind, _dates(d), ", ".join(d.get("occupation", [])[:3]),
                                      ", ".join(d.get("birth_place", [])[:1])] if x)
        snippet = (hl.get(iri, {}).get("abstract") or [None])[0]
        if snippet:
            snippet = esc(snippet).replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")
        elif d.get("abstract"):
            snippet = esc(d["abstract"][:220]) + ("…" if len(d["abstract"]) > 220 else "")
        dsl = " ".join(f'<span class="jl-ds">{esc(x)}</span>' for x in d.get("dataset", [])[:4])
        src = f' · {d["sources"]} sources' if d.get("sources", 0) > 1 else ""
        ep = ""
        if d.get("ep") and not iri.startswith("http://data.judaicalink.org/data/ep/"):
            ep = f' · <a href="{esc(href(d["ep"]))}">entity page</a>'
        out.append(f'<li><h3 dir="auto"><a href="{esc(href(iri))}">{esc(d.get("pref") or iri)}</a></h3>'
                   f'<p class="jl-meta">{esc(meta)}{src}{ep}</p>'
                   + (f'<p class="gs-snippet" dir="auto">{snippet}</p>' if snippet else "")
                   + f'<p class="gs-dsline">{dsl}</p></li>')
    pager = ""
    if n > PER_PAGE:
        cur = start // PER_PAGE + 1
        last = math.ceil(n / PER_PAGE)
        prev = f'<a href="{esc(_url(q, ds, filters, max(0, start - PER_PAGE)))}">← previous</a>' if start else ""
        nxt = f'<a href="{esc(_url(q, ds, filters, start + PER_PAGE))}">next →</a>' if cur < last else ""
        pager = f'<p class="gs-pager">{prev} <span class="jl-meta">page {cur:,} of {last:,}</span> {nxt}</p>'
    what = "entity pages" if ds == ["ep"] else "records"
    head = f"{n:,} {what}" + (f" for “{esc(q)}”" if q else "")
    body = f"""<h1>Graph search</h1>
{form}
<div class="gs-layout"><aside class="gs-side">{''.join(side)}</aside>
<section><p class="gs-count">{head}</p><ol class="gs-results">{''.join(out)}</ol>{pager}</section></div>"""
    return page("Graph search" + (f": {q}" if q else ""), body, head='<link rel="stylesheet" href="/search/static/search.css">',
                description="Search the JudaicaLink knowledge graph: entity pages and the records of all datasets.")
