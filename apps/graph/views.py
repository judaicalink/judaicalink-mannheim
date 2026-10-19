"""The views of JudaicaLink IRIs (decision 0002): entity pages, records, datasets, ontology terms."""

import re
import urllib.parse

import sparql
from common import (DATA, DS, FRANKFURT, ONTO, PREFIXES, RDF_TYPE, esc, href, local, qname, labels,
                    dataset_of_graph, generated, registry, query_link, page)

JL = ONTO
SKOS = PREFIXES["skos"]
OWL = PREFIXES["owl"]
EP = DATA + "data/ep/"

# the facts of an entity page, in this order (property, heading)
EP_FACTS = [
    (JL + "birthDateNormalized", "Born"), (JL + "birthDate", "Born (as recorded)"),
    (JL + "birthLocationURI", "Place of birth"), (JL + "birthLocation", "Place of birth (as recorded)"),
    (JL + "deathDateNormalized", "Died"), (JL + "deathDate", "Died (as recorded)"),
    (JL + "deathLocationURI", "Place of death"), (JL + "deathLocation", "Place of death (as recorded)"),
    (JL + "occupationURI", "Occupation"), (JL + "occupation", "Occupation (as recorded)"),
]
AUTHORITIES = [("d-nb.info/gnd/", "GND"), ("viaf.org/", "VIAF"), ("wikidata.org/", "Wikidata"),
               ("dbpedia.org/", "DBpedia"), ("geonames.org/", "GeoNames"), ("id.loc.gov/", "Library of Congress"),
               ("nli.org.il", "National Library of Israel"), ("deutsche-biographie.de/", "Deutsche Biographie"),
               ("steinheim-institut.de", "Steinheim-Institut"), ("freebase.com/", "Freebase")]
FORMATS = {".ttl": "text/turtle", ".nt": "application/n-triples", ".jsonld": "application/ld+json"}


class Response:
    def __init__(self, status=200, body="", ctype="text/html; charset=utf-8", headers=None):
        self.status, self.body, self.ctype, self.headers = status, body, ctype, headers or {}


def authority(iri):
    for frag, name in AUTHORITIES:
        if frag in iri:
            return name
    return urllib.parse.urlparse(iri).netloc or "other"


def term_html(t, lab=None, link=True):
    """A value: IRIs linked (JudaicaLink IRIs on this platform), literals with language or datatype noted."""
    if t.is_iri:
        text = lab.get(t.value) if lab else None
        if not text and t.value.startswith(DATA + "data/") and t.value.count("/") >= 5:
            text = urllib.parse.unquote(local(t.value)).replace("_", " ")    # e.g. data/occupation/Rabbi
        shown = esc(text) if text else esc(qname(t.value) if not t.value.startswith(DATA) else t.value[len(DATA):])
        if not link:
            return shown
        ext = "" if t.value.startswith(DATA) else ' class="jl-ext"'
        return f'<a href="{esc(href(t.value))}"{ext}>{shown}</a>'
    v = t.value
    if t.datatype.endswith("#HTML"):
        v = re.sub(r"<[^>]+>", " ", v)
    note = f' <span class="jl-meta">@{esc(t.lang)}</span>' if t.lang else ""
    if t.datatype and not t.datatype.startswith(PREFIXES["xsd"]) and not t.datatype.endswith("#HTML"):
        note = f' <span class="jl-meta">{esc(qname(t.datatype))}</span>'
    if len(v) > 600:
        return f'<details class="jl-long"><summary dir="auto">{esc(v[:280])}…</summary><div dir="auto">{esc(v)}</div></details>'
    return f'<span dir="auto">{esc(v)}</span>{note}'


def rdf(iri, mime, also_history=False):
    """The triples of an IRI (as subject, in all graphs) in the requested format, made by Fuseki."""
    q = f"CONSTRUCT {{ <{iri}> ?p ?o }} WHERE {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}"
    return Response(200, sparql.construct(q, accept=mime), mime + "; charset=utf-8", {"Vary": "Accept"})


def wants_rdf(path, accept):
    for ext, mime in FORMATS.items():
        if path.endswith(ext):
            return path[: -len(ext)], mime
    accept = accept or ""
    if "text/html" not in accept:
        for mime in ("text/turtle", "application/n-triples", "application/ld+json"):
            if mime in accept:
                return path, mime
    return path, None


def triples_of(iri):
    rows = sparql.select(f"SELECT ?g ?p ?o WHERE {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}")
    return [(r["g"].value, r["p"].value, r["o"]) for r in rows]


def incoming(iri, limit=60):
    rows = sparql.select(f"SELECT ?g ?s ?p WHERE {{ GRAPH ?g {{ ?s ?p <{iri}> }} }} LIMIT {limit + 1}")
    return [(r["g"].value, r["s"].value, r["p"].value) for r in rows]


def showcase_links(iris):
    """Showcases that present some of these IRIs: the registry's `datasets` and `resolve` (decision 0002)."""
    out = []
    shows = [s for s in registry() if s.get("datasets") and s.get("resolve")]
    if not shows or not iris:
        return out
    values = " ".join(f"<{i}>" for i in iris[:50])
    # records with a class first: deprecated IRIs (e.g. replaced ones) usually have none
    rows = sparql.select(f"""SELECT ?i ?g (MAX(?t) AS ?typed) WHERE {{ VALUES ?i {{ {values} }} GRAPH ?g {{ ?i ?p ?o }}
                             BIND(IF(?p = <{RDF_TYPE}>, 1, 0) AS ?t) }} GROUP BY ?i ?g""")
    present = {}
    for r in rows:
        present.setdefault(dataset_of_graph(r["g"].value), {})[r["i"].value] = int(r["typed"].value)
    for s in shows:
        hits = {}
        for d in s["datasets"]:
            for i, typed in present.get(d, {}).items():
                hits[i] = max(typed, hits.get(i, 0))
        if hits:
            out.append((s, sorted(hits, key=lambda i: (-hits[i], i))[0]))
    return out


# --- entity pages ----------------------------------------------------------------------------------

def entity_page(iri, triples):
    props = {}
    for g, p, o in triples:
        props.setdefault(p, []).append(o)
    one = lambda p: props.get(p, [None])[0]
    # merged: redirect to the page it was merged into (decision 0022 of judaicalink-data)
    if one(JL + "mergedInto"):
        return Response(301, "", headers={"Location": href(one(JL + "mergedInto").value)})
    label = (one(SKOS + "prefLabel") or {"value": local(iri)})["value"]
    classes = [o.value for o in props.get(RDF_TYPE, []) if o.value != JL + "EntityPage"]
    lab = labels([o.value for p in (JL + "birthLocationURI", JL + "deathLocationURI", JL + "occupationURI",
                                    JL + "splitInto") for o in props.get(p, [])] + classes)
    status, note = 200, ""
    if one(JL + "splitInto"):
        parts = "".join(f"<li>{term_html(o, lab)}</li>" for o in props[JL + "splitInto"])
        date = one(JL + "splitDate")
        status = 300
        note = (f'<div class="jl-note"><strong>This entity page was split</strong>{" on " + esc(date.value) if date else ""}'
                f' into these pages:<ul>{parts}</ul></div>')
    elif one(JL + "retiredDate"):
        status = 410
        note = (f'<div class="jl-note"><strong>This entity page was retired</strong> on {esc(one(JL + "retiredDate").value)}:'
                ' its records are no longer grouped into a page of their own.</div>')

    body = [f'<p class="jl-meta"><a href="/search/">Graph search</a> · entity page</p>',
            f'<h1 dir="auto">{esc(label)}</h1>']
    kinds = ", ".join(esc(lab.get(c) or local(c)) for c in classes)
    body.append(f'<p class="jl-lead">{kinds or "Entity"} · <code>{esc(iri)}</code></p>')
    body.append(note)

    alts = props.get(SKOS + "altLabel", [])
    if alts:
        by_lang = {}
        for a in alts:
            by_lang.setdefault(a.lang or "–", []).append(a.value)
        rows = "".join(f'<dt>{esc(k)}</dt><dd dir="auto">{esc(" · ".join(sorted(set(v))))}</dd>'
                       for k, v in sorted(by_lang.items()))
        body.append(f'<details class="jl-alts"><summary>Also known as ({len(alts)} names)</summary>'
                    f'<dl class="jl-facts">{rows}</dl></details>')

    facts = []
    shown = set()
    for p, head in EP_FACTS:
        # a value "as recorded" is left out when it only repeats the normalised one or holds an IRI as text
        vals = [v for v in props.get(p, []) if not (not v.is_iri and (v.value in shown or v.value.startswith("http")))]
        shown.update(v.value for v in vals)
        shown.update(lab.get(v.value, "") for v in vals if v.is_iri)
        if vals:
            facts.append(f'<dt>{esc(head)}</dt><dd>{" · ".join(term_html(v, lab) for v in vals)}</dd>')
    if facts:
        body.append(f'<dl class="jl-facts">{"".join(facts)}</dl>')
    for a in props.get(JL + "hasAbstract", []):
        body.append(f'<blockquote class="jl-abstract" dir="auto">{esc(a.value)}</blockquote>')

    ext = props.get(OWL + "sameAs", [])
    if ext:
        groups = {}
        for o in ext:
            groups.setdefault(authority(o.value), []).append(o.value)
        def ident(u):
            tail = urllib.parse.unquote(u.rstrip("/").rsplit("/", 1)[-1]) or u
            host = urllib.parse.urlparse(u).netloc
            sub = host.split(".")[0] if host.count(".") >= 2 and host.split(".")[0] not in ("www", "d-nb", "viaf", "sws") else ""
            return f'<a href="{esc(u)}" class="jl-ext">{esc(tail)}</a>' + (f' <span class="jl-meta">{esc(sub)}</span>' if sub else "")
        rows = ""
        for k, v in sorted(groups.items()):
            links = " · ".join(ident(u) for u in sorted(v))
            if len(v) > 4:
                links = f"<details><summary>{len(v)} links</summary>{links}</details>"
            rows += f"<dt>{esc(k)}</dt><dd>{links}</dd>"
        body.append(f'<h2>Identifiers</h2><dl class="jl-facts">{rows}</dl>')

    # its records: jl:sameAs since ep 2026-10-19, jl:represents before (judaicalink-data decision 0029)
    records = list(dict.fromkeys(o.value for p in (JL + "sameAs", JL + "represents") for o in props.get(p, [])))
    if records:
        body.append(source_records(records))

    # the showcase gets the entity page's IRI and decides itself which of its records to show (decision 0007)
    shows = showcase_links([iri] + records)
    if shows:
        items = "".join(f'<li><a href="{esc(s["resolve"].format(iri=urllib.parse.quote(iri, safe="")))}">'
                        f'{esc(s["title"])}</a></li>' for s, hit in shows)
        body.append(f'<h2>In the showcases</h2><ul>{items}</ul>')

    history = sparql.select(f"""SELECT ?old ?date WHERE {{ GRAPH <{DS}ep> {{ ?old <{JL}mergedInto> <{iri}> .
                                OPTIONAL {{ ?old <{JL}mergeDate> ?date }} }} }}""")
    if history:
        items = "".join(f'<li><code>{esc(r["old"].value[len(DATA):])}</code>'
                        f'{" (" + esc(r["date"].value) + ")" if "date" in r else ""}</li>' for r in history)
        body.append(f'<h2>History</h2><p>Merged into this page:</p><ul>{items}</ul>')

    body.append(formats_line(iri))
    canonical = FRANKFURT + iri[len(DATA):]
    return Response(status, page(label, "\n".join(body), canonical=canonical, alternates=alternates(iri),
                                 description=f"{label}: JudaicaLink entity page"))


def source_records(records):
    """The records an entity page represents, with the facts each source gives."""
    values = " ".join(f"<{r}>" for r in records)
    rows = sparql.select(f"""SELECT ?r ?g ?p ?o WHERE {{ VALUES ?r {{ {values} }} GRAPH ?g {{ ?r ?p ?o }}
                             FILTER(?p NOT IN (<{OWL}sameAs>, <{JL}sameAs>)) }}""")
    by = {}
    for r in rows:
        by.setdefault(r["r"].value, []).append((r["g"].value, r["p"].value, r["o"]))
    lab = labels([o.value for trs in by.values() for _, p, o in trs if o.is_iri and p != RDF_TYPE][:400]
                 + [p for trs in by.values() for _, p, _ in trs])
    out = [f'<h2>Sources ({len(records)})</h2><div class="jl-sources">']
    for rec in records:
        trs = by.get(rec, [])
        datasets = sorted({dataset_of_graph(g) for g, _, _ in trs})
        title = next((o.value for _, p, o in trs if p in (SKOS + "prefLabel", PREFIXES["rdfs"] + "label",
                                                          PREFIXES["foaf"] + "name")), rec[len(DATA):])
        facts = []
        seen = set()
        for g, p, o in sorted(trs, key=lambda x: (x[1], x[2].value)):
            if p in (RDF_TYPE,) or (p, o.value) in seen:
                continue
            seen.add((p, o.value))
            facts.append(f'<dt>{esc(lab.get(p) or qname(p))}</dt><dd>{term_html(o, lab)}</dd>')
        ds = " ".join(f'<a class="jl-ds" href="/datasets/{esc(d)}">{esc(d)}</a>' for d in datasets)
        out.append(f'<section class="jl-source"><h3 dir="auto"><a href="{esc(href(rec))}">{esc(title)}</a></h3>'
                   f'<p class="jl-meta">{ds}</p><details><summary>{len(facts)} statements</summary>'
                   f'<dl class="jl-facts">{"".join(facts[:80])}</dl></details></section>')
    out.append("</div>")
    return "\n".join(out)


# --- any other record ------------------------------------------------------------------------------

def record_page(iri, triples):
    by_graph = {}
    for g, p, o in triples:
        by_graph.setdefault(g, []).append((p, o))
    lab = labels([o.value for _, _, o in triples if o.is_iri][:400] + [p for _, p, _ in triples])
    label = None
    for p_ in (SKOS + "prefLabel", PREFIXES["rdfs"] + "label", PREFIXES["foaf"] + "name", PREFIXES["dcterms"] + "title"):
        label = next((o.value for _, p, o in triples if p == p_), None)
        if label:
            break
    label = label or iri[len(DATA):]
    classes = sorted({o.value for _, p, o in triples if p == RDF_TYPE})
    eps = sparql.select(f"SELECT ?ep WHERE {{ GRAPH <{DS}ep> {{ ?ep <{JL}sameAs>|<{JL}represents> <{iri}> }} }}")
    body = [f'<p class="jl-meta"><a href="/search/?ds=all">Graph search</a> · record</p>',
            f'<h1 dir="auto">{esc(label)}</h1>',
            f'<p class="jl-lead">{", ".join(term_html(sparql.Term(type="uri", value=c), lab) for c in classes) or "Resource"}'
            f' · <code>{esc(iri)}</code></p>']
    if eps:
        e = eps[0]["ep"].value
        body.append(f'<p class="jl-note">This record is one of the sources of the entity page '
                    f'<a href="{esc(href(e))}">{esc(labels([e]).get(e, e[len(DATA):]))}</a>.</p>')
    shows = showcase_links([iri])
    for s, hit in shows:
        body.append(f'<p><a class="jl-button" href="{esc(s["resolve"].format(iri=urllib.parse.quote(iri, safe="")))}">'
                    f'Show in {esc(s["title"])}</a></p>')
    for g in sorted(by_graph):
        rows = "".join(f'<dt>{esc(lab.get(p) or qname(p))}</dt><dd>{term_html(o, lab)}</dd>'
                       for p, o in sorted(by_graph[g], key=lambda x: (x[0] != RDF_TYPE, x[0], x[1].value)))
        slug = dataset_of_graph(g)
        body.append(f'<h2>From <a href="/datasets/{esc(slug)}">{esc(slug)}</a></h2><dl class="jl-facts">{rows}</dl>')
    inc = incoming(iri)
    if inc:
        ilab = labels([s for _, s, _ in inc] + [p for _, _, p in inc])
        items = "".join(f'<li>{term_html(sparql.Term(type="uri", value=s), ilab)} '
                        f'<span class="jl-meta">{esc(ilab.get(p) or qname(p))} · {esc(dataset_of_graph(g))}</span></li>'
                        for g, s, p in inc[:60])
        more = " (first 60)" if len(inc) > 60 else ""
        body.append(f'<h2>Linked from{more}</h2><ul class="jl-linked">{items}</ul>')
    body.append(formats_line(iri))
    return Response(200, page(label, "\n".join(body), canonical=FRANKFURT + iri[len(DATA):], alternates=alternates(iri)))


def alternates(iri):
    path = href(iri)
    return [(m, path + ext) for ext, m in FORMATS.items()]


def formats_line(iri):
    path = href(iri)
    q = f"SELECT ?g ?p ?o WHERE {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}"
    return (f'<p class="jl-meta jl-formats">As data: <a href="{esc(path)}.ttl">Turtle</a> · '
            f'<a href="{esc(path)}.nt">N-Triples</a> · <a href="{esc(path)}.jsonld">JSON-LD</a> · '
            f'<a href="{esc(query_link(q))}">SPARQL</a> · in production: '
            f'<a href="{esc(FRANKFURT + iri[len(DATA):])}">data.judaicalink.org</a></p>')


def not_found(iri):
    body = (f'<h1>Not in the Mannheim graph</h1><p><code>{esc(iri)}</code> has no statements in the version of the '
            f'graph loaded here.</p><p>It may be known in production: <a href="{esc(FRANKFURT + iri[len(DATA):])}">'
            f'{esc(FRANKFURT + iri[len(DATA):])}</a>. Or <a href="/search/?ds=all">search the graph</a>.</p>')
    return Response(404, page("Not found", body))


def resource(path, accept):
    """/data/<…>: the view of http://data.judaicalink.org/data/<…>."""
    path, mime = wants_rdf(path, accept)
    iri = DATA + path.lstrip("/")
    if mime:
        return rdf(iri, mime)
    triples = triples_of(iri)
    if not triples:
        return not_found(iri)
    if iri.startswith(EP):
        return entity_page(iri, triples)
    return record_page(iri, triples)


# --- datasets --------------------------------------------------------------------------------------

def datasets_index():
    rows = sparql.select(f"""PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX void: <http://rdfs.org/ns/void#>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        SELECT ?d ?title ?version ?triples WHERE {{ GRAPH ?m {{ ?v dcat:isVersionOf ?d .
          OPTIONAL {{ ?v void:triples ?triples }} OPTIONAL {{ ?v dcat:version ?version }}
          OPTIONAL {{ ?d dcterms:title ?title }} }} FILTER(STRSTARTS(STR(?m), "{DS}")) }}""")
    seen = {}
    for r in rows:
        slug = dataset_of_graph(r["d"].value)
        seen.setdefault(slug, r)
    items = []
    for slug in sorted(seen):
        r = seen[slug]
        title = r["title"].value if "title" in r else slug
        n = int(r["triples"].value) if "triples" in r else 0
        items.append(f'<tr><td><a href="/datasets/{esc(slug)}">{esc(slug)}</a></td><td dir="auto">{esc(title)}</td>'
                     f'<td>{esc(r["version"].value) if "version" in r else ""}</td><td class="num">{n:,}</td></tr>')
    body = (f'<h1>Datasets</h1><p class="jl-lead">The datasets loaded on this platform: the stable version of each, '
            f'one named graph per dataset. Full descriptions are in the '
            f'<a href="https://web.judaicalink.org/datasets/">catalogue on web.judaicalink.org</a>.</p>'
            f'<div class="jl-scroll"><table class="jl-table"><thead><tr><th>Dataset</th><th>Title</th><th>Version</th>'
            f'<th class="num">Triples</th></tr></thead><tbody>{"".join(items)}</tbody></table></div>')
    return Response(200, page("Datasets", body))


def dataset_page(slug, accept):
    slug, mime = wants_rdf(slug, accept)
    d = DS + slug
    if mime:
        q = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{d}/meta> {{ ?s ?p ?o }} }}"
        return Response(200, sparql.construct(q, accept=mime), mime + "; charset=utf-8", {"Vary": "Accept"})
    rows = sparql.select(f"SELECT ?s ?p ?o WHERE {{ GRAPH <{d}/meta> {{ ?s ?p ?o }} }}")
    if not rows:
        # not a dataset: a version, an activity, an agent, a term of the vocabulary … (datasets/<…>)
        triples = triples_of(d)
        return record_page(d, triples) if triples else not_found(d)
    lab = labels([r["p"].value for r in rows])
    subj = {}
    for r in rows:
        subj.setdefault(r["s"].value, []).append((r["p"].value, r["o"]))
    title = next((o.value for s, trs in subj.items() for p, o in trs if p == PREFIXES["dcterms"] + "title"), slug)
    stats = (generated("graph-stats.json", {}) or {}).get("datasets", {}).get(slug, {})
    body = [f'<p class="jl-meta"><a href="/datasets/">Datasets</a></p><h1 dir="auto">{esc(title)}</h1>',
            f'<p class="jl-lead"><code>{esc(d)}</code></p>',
            f'<p><a class="jl-button" href="/search/?ds={esc(slug)}">Search this dataset</a> '
            f'<a href="https://web.judaicalink.org/datasets/{esc(slug)}/">In the catalogue</a> · '
            f'<a href="{esc(query_link(f"SELECT ?s ?p ?o WHERE {{ GRAPH <{d}> {{ ?s ?p ?o }} }} LIMIT 100"))}">Query</a></p>']
    if stats.get("classes"):
        cl = labels(list(stats["classes"]))
        items = "".join(f'<tr><td>{term_html(sparql.Term(type="uri", value=c), cl)}</td><td class="num">{n:,}</td></tr>'
                        for c, n in sorted(stats["classes"].items(), key=lambda x: -x[1]))
        body.append(f'<h2>Classes</h2><table class="jl-table"><tbody>{items}</tbody></table>')
    order = [d, d + "/"]
    for s in sorted(subj, key=lambda x: (x not in order, x)):
        facts = "".join(f'<dt>{esc(lab.get(p) or qname(p))}</dt><dd>{term_html(o, lab)}</dd>' for p, o in subj[s])
        head = "Description" if s == d else f"<code>{esc(s[len(DATA):] if s.startswith(DATA) else s)}</code>"
        body.append(f'<h2>{head}</h2><dl class="jl-facts">{facts}</dl>')
    return Response(200, page(title, "\n".join(body), canonical=FRANKFURT + d[len(DATA):],
                              alternates=[(m, f"/datasets/{slug}{e}") for e, m in FORMATS.items()]))


# --- ontology --------------------------------------------------------------------------------------

def ontology_index():
    usage = generated("ontology-usage.json", {}) or {}
    rows = sparql.select(f"""SELECT ?t ?type ?label WHERE {{ GRAPH <{DS}ontology> {{ ?t a ?type
        OPTIONAL {{ ?t <{PREFIXES["rdfs"]}label> ?label }} }} FILTER(STRSTARTS(STR(?t), "{ONTO}")) }}""")
    terms = {}
    for r in rows:
        t = terms.setdefault(r["t"].value, {"types": set(), "label": ""})
        t["types"].add(local(r["type"].value))
        if "label" in r:
            t["label"] = r["label"].value
    used = usage.get("terms", {})
    items = "".join(
        f'<tr><td><a href="/ontology/{esc(local(t))}">jl:{esc(local(t))}</a></td><td>{esc(v["label"])}</td>'
        f'<td>{esc(", ".join(sorted(v["types"])))}</td><td class="num">{used.get(t, {}).get("total", 0):,}</td></tr>'
        for t, v in sorted(terms.items()))
    undefined = [t for t in used if t not in terms]
    und = ""
    if undefined:
        und = ("<h2>Used in the data, not defined in the ontology</h2><ul>" +
               "".join(f'<li><a href="/ontology/{esc(local(t))}">jl:{esc(local(t))}</a> '
                       f'({used[t]["total"]:,})</li>' for t in sorted(undefined)) + "</ul>")
    note = "" if usage else '<p class="jl-note">The usage figures are computed after each load (not yet available).</p>'
    body = (f'<h1>Ontology</h1><p class="jl-lead">The terms of the JudaicaLink ontology (<code>{ONTO}</code>) as loaded '
            f'here, and how often the graph uses them. The documentation is on '
            f'<a href="https://ontology.judaicalink.org/judaicalink-ontology">ontology.judaicalink.org</a>.</p>{note}'
            f'<div class="jl-scroll"><table class="jl-table"><thead><tr><th>Term</th><th>Label</th><th>Kind</th>'
            f'<th class="num">Uses</th></tr></thead><tbody>{items}</tbody></table></div>{und}')
    return Response(200, page("Ontology", body))


def ontology_term(name, accept):
    name, mime = wants_rdf(name, accept)
    iri = ONTO + name
    if mime:
        return rdf(iri, mime)
    rows = sparql.select(f"SELECT ?p ?o WHERE {{ GRAPH <{DS}ontology> {{ <{iri}> ?p ?o }} }}")
    use = ((generated("ontology-usage.json", {}) or {}).get("terms", {})).get(iri)
    if not rows and not use:
        return not_found(iri)
    lab = labels([r["p"].value for r in rows] + [r["o"].value for r in rows if r["o"].is_iri])
    facts = "".join(f'<dt>{esc(lab.get(r["p"].value) or qname(r["p"].value))}</dt><dd>{term_html(r["o"], lab)}</dd>'
                    for r in rows)
    body = [f'<p class="jl-meta"><a href="/ontology/">Ontology</a></p><h1>jl:{esc(name)}</h1>',
            f'<p class="jl-lead"><code>{esc(iri)}</code></p>']
    if rows:
        body.append(f'<dl class="jl-facts">{facts}</dl>')
        body.append(f'<p><a href="https://ontology.judaicalink.org/judaicalink-ontology#jl{esc(name.lower())}">'
                    f'Documentation on ontology.judaicalink.org</a></p>')
    else:
        body.append('<p class="jl-note">This term is used in the data but not defined in the ontology.</p>')
    if use:
        items = "".join(f'<tr><td><a href="/datasets/{esc(d)}">{esc(d)}</a></td><td class="num">{n:,}</td></tr>'
                        for d, n in sorted(use["datasets"].items(), key=lambda x: -x[1]))
        kind = "as a class" if use.get("kind") == "class" else "as a property"
        body.append(f'<h2>Use in the graph ({use["total"]:,} {kind})</h2><table class="jl-table"><tbody>{items}</tbody></table>')
    pat = f"?s a <{iri}>" if use and use.get("kind") == "class" else f"?s <{iri}> ?o"
    q = f"SELECT * WHERE {{ GRAPH ?g {{ {pat} }} }} LIMIT 8"
    ex = sparql.select(q)
    if ex:
        exl = labels([r["s"].value for r in ex])
        items = "".join(f'<li>{term_html(r["s"], exl)}' + (f' → {term_html(r["o"])}' if "o" in r else "") + "</li>" for r in ex)
        body.append(f'<h2>Examples</h2><ul>{items}</ul><p class="jl-meta"><a href="{esc(query_link(q))}">Query</a></p>')
    return Response(200, page(f"jl:{name}", "\n".join(body), canonical=FRANKFURT + iri[len(DATA):]))
