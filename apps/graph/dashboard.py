"""The graph dashboard (/dashboard/, decision 0006): figures of the loaded graph, computed after every load from the
internal SPARQL service and written as one static page (with the platform bar) plus its data as JSON."""

import json
import re
import time

import sparql
from common import DATA, DS, ONTO, GENERATED, esc, generated, href, local, query_link, dataset_of_graph

JL = ONTO
P = """PREFIX jl: <http://data.judaicalink.org/ontology/> PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX owl: <http://www.w3.org/2002/07/owl#> PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#> PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
EPG = f"<{DS}ep>"

QUERIES = {
    "ep_classes": f"""SELECT ?class (COUNT(?e) AS ?pages) WHERE {{ GRAPH {EPG} {{ ?e a ?class }}
        FILTER(?class != jl:EntityPage) }} GROUP BY ?class ORDER BY DESC(?pages)""",
    "ep_history": f"""SELECT ?event (COUNT(DISTINCT ?x) AS ?n) WHERE {{ GRAPH {EPG} {{
        {{ ?x a ?c BIND("in use" AS ?event) }} UNION {{ ?x jl:mergedInto ?t BIND("merged" AS ?event) }}
        UNION {{ ?x jl:splitInto ?t BIND("split" AS ?event) }} UNION {{ ?x jl:retiredDate ?t BIND("retired" AS ?event) }} }} }}
        GROUP BY ?event""",
    "ep_sources": f"""SELECT ?sources (COUNT(?e) AS ?pages) WHERE {{ {{ SELECT ?e (COUNT(?r) AS ?sources)
        WHERE {{ GRAPH {EPG} {{ ?e jl:sameAs|jl:represents ?r }} }} GROUP BY ?e }} }} GROUP BY ?sources ORDER BY ?sources""",
    "ep_by_dataset": f"""SELECT ?g (COUNT(DISTINCT ?e) AS ?pages) (COUNT(DISTINCT ?r) AS ?records) WHERE {{
        GRAPH {EPG} {{ ?e jl:sameAs|jl:represents ?r }} GRAPH ?g {{ ?r a ?c }} FILTER(?g != {EPG}) }} GROUP BY ?g ORDER BY DESC(?pages)""",
    "births": f"""SELECT ?decade (COUNT(?e) AS ?persons) WHERE {{ GRAPH {EPG} {{ ?e a foaf:Person ; jl:birthDateNormalized ?d }}
        BIND(xsd:integer(SUBSTR(STR(?d), 1, 3)) * 10 AS ?decade) FILTER(?decade >= 1000 && ?decade <= 2020) }}
        GROUP BY ?decade ORDER BY ?decade""",
    "deaths": f"""SELECT ?decade (COUNT(?e) AS ?persons) WHERE {{ GRAPH {EPG} {{ ?e a foaf:Person ; jl:deathDateNormalized ?d }}
        BIND(xsd:integer(SUBSTR(STR(?d), 1, 3)) * 10 AS ?decade) FILTER(?decade >= 1000 && ?decade <= 2020) }}
        GROUP BY ?decade ORDER BY ?decade""",
    "birthplaces": f"""SELECT ?place (COUNT(DISTINCT ?e) AS ?persons) WHERE {{ GRAPH {EPG} {{ ?e jl:birthLocation ?place }} }}
        GROUP BY ?place ORDER BY DESC(?persons) LIMIT 20""",
    "occupations": f"""SELECT ?occupation (COUNT(DISTINCT ?e) AS ?persons) WHERE {{ GRAPH {EPG} {{ ?e jl:occupationURI ?occupation }} }}
        GROUP BY ?occupation ORDER BY DESC(?persons) LIMIT 20""",
    "authorities": f"""SELECT ?host (COUNT(*) AS ?links) WHERE {{ GRAPH {EPG} {{ ?e owl:sameAs ?x }}
        BIND(REPLACE(STR(?x), "^https?://([^/]+).*$", "$1") AS ?host) }} GROUP BY ?host ORDER BY DESC(?links) LIMIT 15""",
    "kinds": """PREFIX dcterms: <http://purl.org/dc/terms/>
        SELECT ?m ?kind WHERE { GRAPH ?m { ?d dcterms:type ?kind }
        FILTER(STRSTARTS(STR(?kind), "http://data.judaicalink.org/datasets/vocabulary/kind/")) }""",
    "provenance": """SELECT ?m ?p (COUNT(*) AS ?n) WHERE { GRAPH ?m { ?s ?p ?o } FILTER(STRENDS(STR(?m), "/meta"))
        VALUES ?p { <http://purl.org/dc/terms/license> <http://purl.org/dc/terms/creator> <http://purl.org/dc/terms/issued>
                    <http://purl.org/dc/terms/description> <http://www.w3.org/ns/prov#wasDerivedFrom>
                    <http://www.w3.org/ns/prov#wasGeneratedBy> <http://purl.org/dc/terms/source> } } GROUP BY ?m ?p""",
}
PROV = [("http://purl.org/dc/terms/description", "Description"), ("http://purl.org/dc/terms/license", "Licence"),
        ("http://purl.org/dc/terms/creator", "Creators"), ("http://purl.org/dc/terms/issued", "Issued"),
        ("http://purl.org/dc/terms/source", "Sources"), ("http://www.w3.org/ns/prov#wasDerivedFrom", "Inputs"),
        ("http://www.w3.org/ns/prov#wasGeneratedBy", "Generation")]


def run():
    out = {}
    for name, q in QUERIES.items():
        t = time.time()
        rows = sparql.select(P + q, timeout=3600)
        out[name] = [{k: v.value for k, v in r.items()} for r in rows]
        print(f"  {name}: {len(rows)} rows, {time.time() - t:.1f} s", flush=True)
    return out


def num(x):
    return f"{int(float(x)):,}"


def qlink(name):
    return f'<a class="jl-query" href="{esc(query_link(P + QUERIES[name]))}">query</a>'


def bars_h(rows, label, value, link=None, max_rows=20):
    """Horizontal bars, one series, values written at the bars (direct labels)."""
    rows = rows[:max_rows]
    if not rows:
        return "<p class='jl-meta'>No data.</p>"
    top = max(float(r[value]) for r in rows) or 1
    items = []
    for r in rows:
        v = float(r[value])
        lab = esc(r[label])
        if link:
            lab = f'<a href="{esc(link(r))}">{lab}</a>'
        items.append(f'<div class="db-row"><div class="db-lab" dir="auto">{lab}</div>'
                     f'<div class="db-track"><div class="db-bar" style="width:{max(0.5, 100 * v / top):.1f}%" '
                     f'title="{esc(r[label])}: {v:,.0f}"></div></div><div class="db-val">{v:,.0f}</div></div>')
    return f'<div class="db-hbars">{"".join(items)}</div>'


def bars_v(rows, x, y, title):
    """Columns over decades (one series) as SVG; native tooltips; the table below the chart for exact values."""
    if not rows:
        return "<p class='jl-meta'>No data.</p>"
    data = [(int(float(r[x])), float(r[y])) for r in rows]
    lo, hi = data[0][0], data[-1][0]
    xs = list(range(lo, hi + 10, 10))
    vals = dict(data)
    top = max(vals.values()) or 1
    w, h, pad, bottom = 760, 220, 40, 24
    bw = (w - pad) / len(xs)
    marks, ticks = [], []
    for i, d in enumerate(xs):
        v = vals.get(d, 0)
        bh = (h - bottom - 10) * v / top
        x0 = pad + i * bw
        if v:
            marks.append(f'<rect x="{x0 + 1:.1f}" y="{h - bottom - bh:.1f}" width="{max(1, bw - 2):.1f}" height="{bh:.1f}" '
                         f'rx="2" class="db-col"><title>{d}s: {v:,.0f}</title></rect>')
        if d % 100 == 0:
            ticks.append(f'<text x="{x0 + bw / 2:.1f}" y="{h - 6}" class="db-tick">{d}</text>')
    grid = "".join(f'<line x1="{pad}" x2="{w}" y1="{h - bottom - (h - bottom - 10) * f:.1f}" y2="{h - bottom - (h - bottom - 10) * f:.1f}" class="db-grid"/>'
                   f'<text x="{pad - 6}" y="{h - bottom - (h - bottom - 10) * f + 4:.1f}" class="db-tick db-ytick">{top * f:,.0f}</text>'
                   for f in (0.5, 1.0))
    table = "".join(f"<tr><td>{d}s</td><td class='num'>{v:,.0f}</td></tr>" for d, v in data)
    return (f'<svg viewBox="0 0 {w} {h}" class="db-svg" role="img" aria-label="{esc(title)}">{grid}'
            f'<line x1="{pad}" x2="{w}" y1="{h - bottom}" y2="{h - bottom}" class="db-axis"/>{"".join(marks)}{"".join(ticks)}</svg>'
            f'<details class="db-table"><summary>Table</summary><table class="jl-table"><tbody>{table}</tbody></table></details>')


def build():
    t0 = time.time()
    print("dashboard: queries", flush=True)
    d = run()
    stats = generated("graph-stats.json", {}) or {}
    status = generated("status.json", {}) or {}
    usage = generated("ontology-usage.json", {}) or {}
    datasets = stats.get("datasets", {})
    hist = {r["event"]: int(r["n"]) for r in d["ep_history"]}
    pages = hist.get("in use", 0)
    persons = next((int(r["pages"]) for r in d["ep_classes"] if r["class"].endswith("/Person")), 0)
    ext = sum(int(r["links"]) for r in d["authorities"])
    kinds = {}
    for r in d["kinds"]:
        kinds.setdefault(dataset_of_graph(r["m"]), []).append(local(r["kind"]))
    by_ds = {dataset_of_graph(r["g"]): r for r in d["ep_by_dataset"]}
    prov = {}
    for r in d["provenance"]:
        prov.setdefault(dataset_of_graph(r["m"]), set()).add(r["p"])
    (GENERATED / "dashboard").mkdir(parents=True, exist_ok=True)
    (GENERATED / "dashboard" / "dashboard.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    tiles = [
        (f'{status.get("data_triples", 0):,}', "triples in", f'{status.get("datasets", 0)} datasets', "/datasets/"),
        (f"{pages:,}", "entity pages", f"{persons:,} of them persons", "/search/"),
        (f"{sum(int(r['records']) for r in d['ep_by_dataset']):,}", "records", "grouped into entity pages", None),
        (f"{ext:,}", "links", "from entity pages to authority files and other sources", None),
        (f"{len(usage.get('terms', {})):,}", "ontology terms", "in use", "/ontology/"),
    ]
    tiles_html = "".join(f'<div class="db-tile"><div class="db-big">{a}</div><div>{esc(b)}</div>'
                         f'<div class="jl-meta">{esc(c)}</div>{f"<a href={chr(34)}{u}{chr(34)} class=db-more>more</a>" if u else ""}</div>'
                         for a, b, c, u in tiles)

    # datasets table
    rows = []
    for slug, info in sorted(datasets.items(), key=lambda x: -x[1].get("triples", 0)):
        ep = by_ds.get(slug)
        cls = info.get("classes", {})
        main = ", ".join(list(dict.fromkeys(local(c) for c, _ in sorted(cls.items(), key=lambda x: -x[1])))[:2])
        cov = len(prov.get(slug, set()))
        rows.append(f'<tr><td><a href="/datasets/{esc(slug)}">{esc(slug)}</a><div class="jl-meta" dir="auto">{esc(info.get("title", ""))}</div></td>'
                    f'<td>{esc(", ".join(kinds.get(slug, [])))}</td><td>{esc(info.get("version", ""))}</td>'
                    f'<td class="num">{info.get("triples", 0):,}</td><td>{esc(main)}</td>'
                    f'<td class="num">{num(ep["records"]) if ep else ""}</td>'
                    f'<td class="num">{cov}/{len(PROV)}</td></tr>')
    ds_table = (f'<div class="jl-scroll"><table class="jl-table"><thead><tr><th>Dataset</th><th>Kind</th><th>Version</th>'
                f'<th class="num">Triples</th><th>Main classes</th><th class="num">Records on entity pages</th>'
                f'<th class="num">Provenance</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    prov_rows = []
    for slug in sorted(datasets):
        cells = "".join(f'<td class="db-dot">{"●" if p in prov.get(slug, set()) else "<span class=jl-meta>·</span>"}</td>' for p, _ in PROV)
        prov_rows.append(f'<tr><td><a href="/datasets/{esc(slug)}">{esc(slug)}</a></td>{cells}</tr>')
    prov_table = (f'<div class="jl-scroll"><table class="jl-table db-prov"><thead><tr><th>Dataset</th>'
                  + "".join(f"<th>{esc(h)}</th>" for _, h in PROV) + f'</tr></thead><tbody>{"".join(prov_rows)}</tbody></table></div>')

    occ = [{"occupation": local(r["occupation"]).replace("_", " "), "persons": r["persons"], "iri": r["occupation"]}
           for r in d["occupations"]]
    ds_bars = [{"dataset": dataset_of_graph(r["g"]), "pages": r["pages"]} for r in d["ep_by_dataset"]]
    hist_rows = [{"event": k, "n": hist.get(k, 0)} for k in ("in use", "merged", "split", "retired")]
    cls_rows = [{"class": local(r["class"]), "pages": r["pages"]} for r in d["ep_classes"]]
    src_rows = [{"sources": r["sources"], "pages": r["pages"]} for r in d["ep_sources"]]

    body = f"""<h1>The knowledge graph</h1>
<p class="jl-lead">Figures of the JudaicaLink knowledge graph as loaded on this platform ({esc(status.get("made", "")[:10])}).
Every figure links to the query that computes it.</p>
<div class="db-tiles">{tiles_html}</div>

<h2>Entity pages</h2>
<p>An entity page brings the records of all sources about one person, place, work or subject together
(<a href="/search/">search them</a>). Its IRI stays stable: pages that are merged point to the page they went into,
split pages to their parts.</p>
<div class="db-grid2">
<section><h3>Kinds {qlink("ep_classes")}</h3>{bars_h(cls_rows, "class", "pages")}</section>
<section><h3>Page IRIs {qlink("ep_history")}</h3>{bars_h(hist_rows, "event", "n")}
<p class="jl-meta">Retired IRIs are former pages whose records no longer form a page of their own.</p></section>
<section><h3>Sources per page {qlink("ep_sources")}</h3>{bars_h(src_rows, "sources", "pages", max_rows=12)}</section>
<section><h3>Pages per source dataset {qlink("ep_by_dataset")}</h3>{bars_h(ds_bars, "dataset", "pages", link=lambda r: "/datasets/" + r["dataset"])}</section>
</div>

<h2>People</h2>
<h3>Births per decade {qlink("births")}</h3>{bars_v(d["births"], "decade", "persons", "Births per decade")}
<h3>Deaths per decade {qlink("deaths")}</h3>{bars_v(d["deaths"], "decade", "persons", "Deaths per decade")}
<div class="db-grid2">
<section><h3>Places of birth (as recorded) {qlink("birthplaces")}</h3>{bars_h(d["birthplaces"], "place", "persons")}</section>
<section><h3>Occupations {qlink("occupations")}</h3>{bars_h(occ, "occupation", "persons", link=lambda r: href(r["iri"]))}</section>
</div>

<h2>Links</h2>
<section><h3>Where entity pages link to {qlink("authorities")}</h3>{bars_h(d["authorities"], "host", "links")}</section>

<h2>Datasets</h2>
{ds_table}
<h3>What the descriptions record {qlink("provenance")}</h3>
<p class="jl-meta">Every dataset is described in its own graph (<code>…/datasets/&lt;slug&gt;/meta</code>): VoID, DCAT and PROV.</p>
{prov_table}
<p class="jl-meta">Made {esc(time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))} by the platform's dashboard job.
Figures for Compact Memory are in its <a href="/compact-memory/dashboard/">own dashboard</a>.</p>
"""
    from common import page
    html = page("Dashboard", body, head='<link rel="stylesheet" href="/search/static/dashboard.css">',
                description="Figures of the JudaicaLink knowledge graph as loaded on mannheim.judaicalink.org")
    (GENERATED / "dashboard" / "index.html").write_text(html, encoding="utf-8")
    print(f"dashboard written in {time.time() - t0:.0f} s", flush=True)
