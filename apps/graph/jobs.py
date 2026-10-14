#!/usr/bin/env python3
"""The jobs of the graph application, run after every load (services/load.sh) or by hand:

    python3 jobs.py stats      figures of the loaded graph: status.json, graph-stats.json, ontology-usage.json
    python3 jobs.py index <core>   the Solr core `graph` for the graph search: filled into <core> (made before by
                                   services/solr-core.sh), then swapped in
    python3 jobs.py dashboard  the graph dashboard (/dashboard/) from the figures
    python3 jobs.py all        stats and dashboard (the index needs a new core first: services/jobs.sh)

They read the internal SPARQL service (no time limit) and write into JL_GENERATED.
"""

import json
import re
import sys
import time
from pathlib import Path

import sparql
import solr
from common import DATA, DS, ONTO, PREFIXES, RDF_TYPE, GENERATED, dataset_of_graph, local

JL = ONTO
SKOS, RDFS, FOAF, DCT, OWL = (PREFIXES[p] for p in ("skos", "rdfs", "foaf", "dcterms", "owl"))
GNDO, SCHEMA = PREFIXES["gndo"], PREFIXES["schema"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def write(name, data):
    GENERATED.mkdir(parents=True, exist_ok=True)
    tmp = GENERATED / (name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.rename(GENERATED / name)


# --- stats -----------------------------------------------------------------------------------------

def stats():
    t0 = time.time()
    log("triples per graph")
    graphs = {r["g"].value: int(r["n"].value) for r in sparql.select(
        "SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g", timeout=3600)}
    log("dataset descriptions")
    meta = sparql.select("""PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX void: <http://rdfs.org/ns/void#>
        SELECT ?m ?d ?title ?version ?issued ?stated WHERE { GRAPH ?m { ?v dcat:isVersionOf ?d .
          OPTIONAL { ?d dcterms:title ?title } OPTIONAL { ?v dcat:version ?version }
          OPTIONAL { ?v dcterms:issued ?issued } OPTIONAL { ?v void:triples ?stated } } }""", timeout=3600)
    datasets = {}
    for r in meta:
        if not r["m"].value.endswith("/meta"):
            continue
        slug = dataset_of_graph(r["d"].value)
        d = datasets.setdefault(slug, {"title": slug})
        for k in ("title", "version", "issued"):
            if k in r:
                d[k] = r[k].value
        if "stated" in r:
            d["stated_triples"] = int(r["stated"].value)
    for g, n in graphs.items():
        if g.startswith(DS) and not g.endswith("/meta"):
            datasets.setdefault(dataset_of_graph(g), {"title": dataset_of_graph(g)})["triples"] = n
    log("classes per graph")
    for r in sparql.select("SELECT ?g ?c (COUNT(DISTINCT ?s) AS ?n) WHERE { GRAPH ?g { ?s a ?c } } GROUP BY ?g ?c",
                           timeout=3600):
        slug = dataset_of_graph(r["g"].value)
        if slug in datasets and not r["g"].value.endswith("/meta"):
            datasets[slug].setdefault("classes", {})[r["c"].value] = int(r["n"].value)
    log("ontology usage")
    usage = {}
    for r in sparql.select(f"""SELECT ?g ?p (COUNT(*) AS ?n) WHERE {{ GRAPH ?g {{ ?s ?p ?o }}
            FILTER(STRSTARTS(STR(?p), "{ONTO}")) }} GROUP BY ?g ?p""", timeout=3600):
        if r["g"].value.endswith("/meta") or r["g"].value == DS + "ontology":
            continue
        u = usage.setdefault(r["p"].value, {"kind": "property", "total": 0, "datasets": {}})
        u["datasets"][dataset_of_graph(r["g"].value)] = int(r["n"].value)
        u["total"] += int(r["n"].value)
    for slug, d in datasets.items():
        for c, n in d.get("classes", {}).items():
            if c.startswith(ONTO) and slug != "ontology":
                u = usage.setdefault(c, {"kind": "class", "total": 0, "datasets": {}})
                u["datasets"][slug] = n
                u["total"] += n
    defined = {r["t"].value for r in sparql.select(
        f"SELECT DISTINCT ?t WHERE {{ GRAPH <{DS}ontology> {{ ?t ?p ?o }} }}")}
    write("ontology-usage.json", {"terms": usage, "undefined": sorted(t for t in usage if t not in defined)})
    data_graphs = {g: n for g, n in graphs.items() if not g.endswith("/meta")}
    status = {
        "made": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "graphs": len(graphs), "datasets": len(data_graphs), "triples": sum(graphs.values()),
        "data_triples": sum(data_graphs.values()),
        "versions": {s: d.get("version") for s, d in sorted(datasets.items()) if d.get("version")},
        "endpoint": "https://mannheim.judaicalink.org/sparql",
    }
    write("status.json", status)
    write("graph-stats.json", {"datasets": datasets, "titles": {s: d.get("title", s) for s, d in datasets.items()},
                               "made": status["made"]})
    log(f"stats done in {time.time() - t0:.0f} s: {status['datasets']} datasets, {status['triples']:,} triples")


# --- the search index ------------------------------------------------------------------------------

LABEL = [SKOS + "prefLabel", RDFS + "label", FOAF + "name", DCT + "title", PREFIXES["dc"] + "title",
         GNDO + "preferredNameForThePerson", GNDO + "preferredNameForThePlaceOrGeographicName",
         GNDO + "preferredNameForTheWork", GNDO + "preferredNameForTheSubjectHeading",
         GNDO + "preferredNameForTheCorporateBody", GNDO + "preferredName", SCHEMA + "name"]
ALT = [SKOS + "altLabel", GNDO + "variantNameForThePerson", GNDO + "variantNameForThePlaceOrGeographicName",
       GNDO + "variantName", FOAF + "nick"]
BIRTH = [JL + "birthDateNormalized", JL + "birthYear", JL + "birthDate", GNDO + "dateOfBirth"]
DEATH = [JL + "deathDateNormalized", JL + "deathYear", JL + "deathDate", GNDO + "dateOfDeath"]
BPLACE = [JL + "birthLocationURI", JL + "birthLocation", GNDO + "placeOfBirth"]
OCC = [JL + "occupationURI", JL + "occupation", GNDO + "professionOrOccupation"]
TEXT = [JL + "hasAbstract", DCT + "description", RDFS + "comment", SKOS + "scopeNote", GNDO + "biographicalOrHistoricalInformation"]
STATUS = {JL + "mergedInto": "merged", JL + "splitInto": "split", JL + "retiredDate": "retired"}
LABELSET = set(LABEL)
PROPS = LABEL + ALT + BIRTH + DEATH + BPLACE + OCC + TEXT + [RDF_TYPE, JL + "represents"] + list(STATUS)

FIELD_TYPES = [{
    "name": "text_folded", "class": "solr.TextField", "positionIncrementGap": "100",
    "analyzer": {"tokenizer": {"class": "solr.StandardTokenizerFactory"},
                 "filters": [{"class": "solr.LowerCaseFilterFactory"},
                             {"class": "solr.ASCIIFoldingFilterFactory", "preserveOriginal": "true"}]}}, {
    "name": "text_prefix", "class": "solr.TextField", "positionIncrementGap": "100",
    "indexAnalyzer": {"tokenizer": {"class": "solr.StandardTokenizerFactory"},
                      "filters": [{"class": "solr.LowerCaseFilterFactory"}, {"class": "solr.ASCIIFoldingFilterFactory"},
                                  {"class": "solr.EdgeNGramFilterFactory", "minGramSize": "1", "maxGramSize": "20"}]},
    "queryAnalyzer": {"tokenizer": {"class": "solr.StandardTokenizerFactory"},
                      "filters": [{"class": "solr.LowerCaseFilterFactory"}, {"class": "solr.ASCIIFoldingFilterFactory"}]}}]
FIELDS = [
    {"name": "pref", "type": "string", "stored": True, "indexed": False, "docValues": False},
    {"name": "pref_sort", "type": "string", "stored": False, "docValues": True},
    {"name": "label", "type": "text_general", "multiValued": True, "stored": True},
    {"name": "label_folded", "type": "text_folded", "multiValued": True, "stored": False},
    {"name": "label_prefix", "type": "text_prefix", "multiValued": True, "stored": False},
    {"name": "alt", "type": "text_general", "multiValued": True, "stored": False},
    {"name": "alt_folded", "type": "text_folded", "multiValued": True, "stored": False},
    {"name": "alt_prefix", "type": "text_prefix", "multiValued": True, "stored": False},
    {"name": "text", "type": "text_folded", "multiValued": True, "stored": False},
    {"name": "abstract", "type": "text_folded", "stored": True},
    {"name": "dataset", "type": "string", "multiValued": True, "stored": True, "docValues": True},
    {"name": "classes", "type": "string", "multiValued": True, "stored": True, "docValues": True},
    {"name": "class", "type": "string", "multiValued": True, "stored": True, "docValues": True},
    {"name": "birth", "type": "string", "stored": True, "indexed": False},
    {"name": "death", "type": "string", "stored": True, "indexed": False},
    {"name": "birth_year", "type": "pint", "stored": True, "docValues": True},
    {"name": "century", "type": "string", "stored": True, "docValues": True},
    {"name": "birth_place", "type": "string", "multiValued": True, "stored": True, "docValues": True},
    {"name": "occupation", "type": "string", "multiValued": True, "stored": True, "docValues": True},
    {"name": "ep", "type": "string", "stored": True, "docValues": True},
    {"name": "ep_status", "type": "string", "stored": True, "docValues": True},
    {"name": "sources", "type": "pint", "stored": True, "docValues": True},
]
COPY = [{"source": "label", "dest": ["label_folded", "label_prefix"]}, {"source": "alt", "dest": ["alt_folded", "alt_prefix"]}]
# broad kinds for the facet "Kind", from the classes
KIND = [(r"Person$", "Person"), (r"(Place|PlaceOrGeographicName|City|Country|Settlement|Location)$", "Place"),
        (r"(Work|Book|Article|Periodical|Publication\w*|Manuscript)$", "Work"),
        (r"(CorporateBody|Organi[sz]ation|Institution|Community)$", "Organisation"),
        (r"(Subject|Concept|SubjectHeading|Topic)$", "Subject"), (r"Page$", "Page"), (r"Event$", "Event")]
YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)")


def kind_of(classes):
    out = []
    for c in classes:
        for pat, k in KIND:
            if re.search(pat, local(c)) and k not in out:
                out.append(k)
    return out or (["Other"] if classes else [])


# records that are not looked for by name: pages, mentions and the like (the showcases present them)
HV = DATA + "data/haskala/vocab/"
EXCLUDE = {JL + "Page", JL + "Reference", JL + "CorpusPresence", SCHEMA + "PublicationIssue",
           SCHEMA + "PublicationVolume", PREFIXES["void"] + "Dataset", PREFIXES["dcat"] + "Dataset",
           HV + "Mention", HV + "Production", HV + "Edition", HV + "Preface", HV + "Translation"}


def index(new):
    t0 = time.time()
    graphs = [r["g"].value for r in sparql.select("SELECT DISTINCT ?g WHERE { GRAPH ?g { } }")]
    graphs = sorted(g for g in graphs if g.startswith(DS) and not g.endswith("/meta"))
    recs = {}          # iri -> {"ds": set of datasets, property: [values]}
    skip = set()
    for g in graphs:   # pass 1: classes, and the subjects to leave out
        for s, c in sparql.select_tsv(f"SELECT ?s ?c WHERE {{ GRAPH <{g}> {{ ?s a ?c }} FILTER(!ISBLANK(?s)) }}"):
            if c in EXCLUDE:
                skip.add(s)
    log(f"{len(skip):,} subjects left out (pages, mentions, issues …)")
    values = " ".join(f"<{p}>" for p in PROPS)
    for g in graphs:   # pass 2: the values
        slug = dataset_of_graph(g)
        n = 0
        q = f"SELECT ?s ?p ?o WHERE {{ VALUES ?p {{ {values} }} GRAPH <{g}> {{ ?s ?p ?o }} FILTER(!ISBLANK(?s)) }}"
        for s, p, o in sparql.select_tsv(q):
            if s in skip:
                continue
            r = recs.get(s)
            if r is None:
                r = recs[s] = {"ds": set()}
            if p in LABELSET:      # a record belongs to the datasets that name it, not to those that only add facts
                r["ds"].add(slug)
            r.setdefault(p, []).append(o)
            n += 1
        log(f"{slug}: {n:,} values")
    skip.clear()
    log(f"{len(recs):,} subjects; resolving labels of places and occupations")

    def name(iri):
        r = recs.get(iri)
        if not r:
            return local(iri).replace("_", " ")
        for p in LABEL:
            if r.get(p):
                return r[p][0]
        return local(iri).replace("_", " ")

    represented = {}
    for s, r in recs.items():
        for rec in r.get(JL + "represents", []):
            represented[rec] = s
    # the label of a place IRI may only be known through its entity page (geonames ids): fall back to it
    docs = []
    for s, r in recs.items():
        labels = [v for p in LABEL for v in r.get(p, [])]
        if not labels or not s.startswith("http"):
            continue
        is_ep = s.startswith(DATA + "data/ep/")
        classes = sorted(set(r.get(RDF_TYPE, [])) - {JL + "EntityPage"})
        birth = next((v for p in BIRTH for v in r.get(p, [])), "")
        death = next((v for p in DEATH for v in r.get(p, [])), "")
        y = YEAR.search(birth or "")
        # places: the names as recorded; a place IRI only when it has a label (TGN and many geonames IRIs have none)
        places = [v for v in r.get(JL + "birthLocation", []) if not v.startswith("http")]
        if not places:
            places = [name(v) for p in (JL + "birthLocationURI", GNDO + "placeOfBirth") for v in r.get(p, [])
                      if v in recs and any(recs[v].get(lp) for lp in LABEL)]
        # occupations: labels, or the name in the IRI (data/occupation/Rabbi); literals that only hold an IRI too
        occs = [name(v) if v.startswith("http") else v for p in OCC for v in r.get(p, [])]
        text = [v for p in TEXT for v in r.get(p, [])]
        status = next((st for p, st in STATUS.items() if r.get(p)), "active" if is_ep else None)
        doc = {"id": s, "pref": labels[0], "pref_sort": labels[0].lower()[:200], "label": list(dict.fromkeys(labels))[:30],
               "alt": list(dict.fromkeys(v for p in ALT for v in r.get(p, [])))[:60],
               "dataset": sorted(r["ds"]), "classes": classes, "class": kind_of(classes),
               "sources": len(r.get(JL + "represents", [])) if is_ep else 1}
        if text:
            doc["abstract"] = text[0][:2000]
            doc["text"] = [t[:4000] for t in text[:5]]
        if birth:
            doc["birth"] = birth[:40]
        if death:
            doc["death"] = death[:40]
        if y:
            doc["birth_year"] = int(y.group(1))
            doc["century"] = f"{int(y.group(1)) // 100 + 1}th century"
        if places:
            doc["birth_place"] = sorted(set(places))[:5]
        if occs:
            doc["occupation"] = sorted(set(o.strip() for o in occs if o.strip()))[:10]
        if is_ep:
            doc["ep_status"] = status
        elif s in represented:
            doc["ep"] = represented[s]
        docs.append(doc)
    log(f"{len(docs):,} documents; writing {new}")
    solr.define(new, FIELDS, COPY, FIELD_TYPES)
    for i in range(0, len(docs), 5000):
        solr.add(new, docs[i:i + 5000])
    solr.commit(new)
    solr.optimize(new)
    solr.swap("graph", new)
    log(f"index done in {time.time() - t0:.0f} s: {len(docs):,} documents")


def dashboard():
    import dashboard as d
    d.build()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("stats", "all"):
        stats()
    if what == "index":
        index(sys.argv[2])
    if what in ("dashboard", "all"):
        dashboard()
