"""PubMed: how much has each clinician published on Dupuytren's / Ledderhose?

Name-only author searches return namesakes, so a paper only counts when the matching author's affiliation mentions
the listing's country, region or city. The result is a research signal shown on the listing ("published N papers
on Dupuytren's, mostly on radiotherapy"), not evidence that the clinician offers a treatment.
"""
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

from lib import COUNTRY_NAMES, UA, JsonCache, http_json, strip_accents

_cache = JsonCache("pubmed")
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOPIC = '(dupuytren*[tiab] OR ledderhose[tiab] OR "plantar fibromatosis"[tiab] OR "palmar fibromatosis"[tiab])'
TOPICS = [
    ("radiotherapy", r"radiother|radiation|irradiat|x-ray|orthovoltage"),
    ("collagenase", r"collagenase|xiaflex|xiapex|clostridium"),
    ("needle_aponeurotomy", r"needle|percutaneous|aponeurotomy|fasciotomy"),
    ("fasciectomy", r"fasciectomy|surg|operat"),
    ("steroid_injection", r"steroid|triamcinolone|cortico"),
    ("ledderhose", r"ledderhose|plantar"),
    ("biology", r"gene|genetic|myofibroblast|tnf|cell|molecular|pathogen"),
]
US_STATE_NAMES = None


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _search(last, initial):
    key = f"{last} {initial}"
    if key in _cache:
        return _cache.get(key)
    term = f'"{last} {initial}"[Author] AND {TOPIC}'
    try:
        ids = http_json(EUTILS + "esearch.fcgi", {"db": "pubmed", "term": term, "retmax": 60, "retmode": "json"})[
            "esearchresult"]["idlist"]
        time.sleep(0.35)
        arts = []
        if ids:
            xml = _get(EUTILS + "efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(ids))
            time.sleep(0.35)
            root = ET.fromstring(xml)
            for a in root.iter("PubmedArticle"):
                pmid = a.findtext(".//PMID")
                title = "".join(a.find(".//ArticleTitle").itertext()) if a.find(".//ArticleTitle") is not None else ""
                year = a.findtext(".//PubDate/Year") or (a.findtext(".//PubDate/MedlineDate") or "")[:4]
                journal = a.findtext(".//Journal/ISOAbbreviation") or a.findtext(".//Journal/Title")
                affs = []
                for au in a.iter("Author"):
                    ln = au.findtext("LastName") or ""
                    ini = au.findtext("Initials") or ""
                    if strip_accents(ln).lower() == strip_accents(last).lower() and ini[:1].upper() == initial.upper():
                        affs += [x.text or "" for x in au.iter("Affiliation")]
                arts.append({"pmid": pmid, "title": title, "year": year, "journal": journal, "affs": affs})
    except Exception as e:  # noqa: BLE001
        print("pubmed error", key, e)
        return None
    _cache.set(key, arts)
    return arts


def _place_terms(listing):
    terms = set()
    for l in listing["locations"]:
        cc = l["country"]
        terms.add(COUNTRY_NAMES.get(cc, cc).lower())
        if cc == "US":
            terms |= {"usa", "united states"}
        if cc == "GB":
            terms |= {"uk", "united kingdom", "england", "scotland", "wales"}
        if cc == "NL":
            terms.add("netherlands")
        if cc == "DE":
            terms |= {"germany", "deutschland"}
        for k in ("city",):
            if l.get(k):
                terms.add(strip_accents(l[k]).lower().split(",")[0].strip())
    return {t for t in terms if len(t) > 2}


def run(listings):
    hits = 0
    for m in listings:
        if m["kind"] != "clinician":
            continue
        toks = [t for t in re.split(r"\s+", m["name"].replace(".", " ")) if t]
        if len(toks) < 2:
            continue
        last, initial = toks[-1], toks[0][0]
        arts = _search(last, initial) or []
        places = _place_terms(m)
        good = []
        for a in arts:
            aff = strip_accents(" ".join(a["affs"])).lower()
            if aff and any(p in aff for p in places):
                good.append(a)
        if not good:
            continue
        hits += 1
        topics = {}
        for a in good:
            for name, rx in TOPICS:
                if re.search(rx, a["title"], re.I):
                    topics[name] = topics.get(name, 0) + 1
        good.sort(key=lambda a: a["year"] or "", reverse=True)
        m["publications"] = {
            "count": len(good),
            "topics": dict(sorted(topics.items(), key=lambda kv: -kv[1])),
            "recent": [{k: a[k] for k in ("pmid", "title", "year", "journal")} for a in good[:5]],
            "query": f'"{last} {initial}"[Author] AND Dupuytren/Ledderhose, affiliation matched to listing location',
        }
    _cache.save()
    print(f"pubmed: {hits} clinicians with affiliation-matched Dupuytren/Ledderhose papers")
