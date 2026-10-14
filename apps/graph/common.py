"""What the views, the search and the jobs share: IRIs, prefixes, labels, the page shell."""

import html
import json
import os
import re
import tomllib
import urllib.parse
from pathlib import Path

import sparql

DATA = "http://data.judaicalink.org/"
FRANKFURT = "https://data.judaicalink.org/"           # production: the canonical page of every IRI
GENERATED = Path(os.environ.get("JL_GENERATED", "/generated"))
REGISTRY = Path(os.environ.get("JL_REGISTRY", "/registry/showcases.toml"))
DS = DATA + "datasets/"
ONTO = DATA + "ontology/"

PREFIXES = {
    "jl": ONTO, "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#", "skos": "http://www.w3.org/2004/02/skos/core#",
    "foaf": "http://xmlns.com/foaf/0.1/", "dcterms": "http://purl.org/dc/terms/", "dc": "http://purl.org/dc/elements/1.1/",
    "gndo": "http://d-nb.info/standards/elementset/gnd#", "schema": "http://schema.org/", "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dbo": "http://dbpedia.org/ontology/", "geo": "http://www.opengis.net/ont/geosparql#",
    "wgs84": "http://www.w3.org/2003/01/geo/wgs84_pos#", "prov": "http://www.w3.org/ns/prov#", "void": "http://rdfs.org/ns/void#",
    "dcat": "http://www.w3.org/ns/dcat#", "bibo": "http://purl.org/ontology/bibo/", "edm": "http://www.europeana.eu/schemas/edm/",
    "wdt": "http://www.wikidata.org/prop/direct/", "wd": "http://www.wikidata.org/entity/",
}
LABEL_PROPS = [PREFIXES["skos"] + "prefLabel", PREFIXES["rdfs"] + "label", PREFIXES["foaf"] + "name",
               PREFIXES["dcterms"] + "title", PREFIXES["dc"] + "title",
               PREFIXES["gndo"] + "preferredNameForThePerson", PREFIXES["gndo"] + "preferredNameForThePlaceOrGeographicName",
               PREFIXES["gndo"] + "preferredNameForTheWork", PREFIXES["gndo"] + "preferredNameForTheSubjectHeading",
               PREFIXES["gndo"] + "preferredName", PREFIXES["schema"] + "name", PREFIXES["skos"] + "altLabel"]
RDF_TYPE = PREFIXES["rdf"] + "type"
LANG_ORDER = {"": 0, "en": 1, "de": 2}


def esc(s):
    return html.escape(str(s), quote=True)


def qname(iri):
    for p, ns in sorted(PREFIXES.items(), key=lambda x: -len(x[1])):
        if iri.startswith(ns) and re.fullmatch(r"[\w.-]*", iri[len(ns):]):
            return f"{p}:{iri[len(ns):]}"
    return iri


def local(iri):
    return re.split(r"[/#]", iri.rstrip("/#"))[-1]


def href(iri):
    """The rule of decision 0002: a JudaicaLink IRI is shown on this platform under the same path."""
    if iri.startswith(DATA):
        return "/" + iri[len(DATA):]
    return iri


def dataset_of_graph(g):
    """slug of a dataset graph (…/datasets/<slug>), or of its -meta graph."""
    if g.startswith(DS):
        return g[len(DS):].removesuffix("/meta")
    return g


def best_label(terms):
    """Prefer prefLabel over other properties (the order of LABEL_PROPS), then no language, en, de, others."""
    if not terms:
        return None
    return sorted(terms, key=lambda t: (t[0], LANG_ORDER.get(t[1], 3), t[2]))[0][2]


def labels(iris, extra_graph=None):
    """Labels of many IRIs at once: {iri: label}."""
    iris = [i for i in dict.fromkeys(iris) if i.startswith("http")]
    out = {}
    order = {p: n for n, p in enumerate(LABEL_PROPS)}
    for start in range(0, len(iris), 200):
        chunk = iris[start:start + 200]
        values = " ".join(f"<{i}>" for i in chunk)
        props = " ".join(f"<{p}>" for p in LABEL_PROPS)
        rows = sparql.select(f"SELECT ?s ?p ?l WHERE {{ VALUES ?s {{ {values} }} VALUES ?p {{ {props} }} ?s ?p ?l }}")
        found = {}
        for r in rows:
            found.setdefault(r["s"].value, []).append((order.get(r["p"].value, 99), r["l"].lang, r["l"].value))
        out.update({s: best_label(t) for s, t in found.items()})
    return out


def registry():
    try:
        return tomllib.loads(REGISTRY.read_text(encoding="utf-8")).get("showcase", [])
    except OSError:
        return []


def generated(name, default=None):
    try:
        return json.loads((GENERATED / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def query_link(query):
    """A link to the query in the SPARQL editor (decision 0002: every number links to its query)."""
    return "/sparql/#query=" + urllib.parse.quote(query.strip()) + "&endpoint=" + urllib.parse.quote("/sparql")


def page(title, body, canonical=None, alternates=(), head="", description=""):
    """The HTML shell: the platform bar comes in through nginx (SSI), the look from the kit."""
    links = ""
    if canonical:
        links += f'<link rel="canonical" href="{esc(canonical)}">\n'
    for mime, url in alternates:
        links += f'<link rel="alternate" type="{esc(mime)}" href="{esc(url)}">\n'
    desc = f'<meta name="description" content="{esc(description)}">\n' if description else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · JudaicaLink Mannheim</title>
{desc}{links}<link rel="stylesheet" href="/kit/1/jl.css">
{head}
</head>
<body>
<!--# include virtual="/kit/1/header.html" -->
<main class="jl-main">
{body}
</main>
<footer class="jl-footer">The Mannheim version of the JudaicaLink knowledge graph (<a href="/about/data/">what is loaded</a>).
JudaicaLink runs in production in the portal of the <a href="https://www.jewishstudies.de/en/judaicalink/">FID Jewish Studies</a>.</footer>
</body>
</html>
"""
