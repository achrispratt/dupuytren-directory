"""Merge source entries into listings: one listing per clinician (or per clinic/team when no single doctor is named).

The same doctor often appears on several lists (e.g. IDS radiotherapy list + BDS map). We merge on an ascii-folded
"first-initial lastname" key within a country, and only when the two records also share a region/city, a website
domain or one of them has no location detail. Everything a source said is kept, with its provenance.
"""
import re
import urllib.parse

from lib import person_key, slugify, strip_accents


def _domain(u):
    if not u:
        return None
    d = urllib.parse.urlparse(u).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", strip_accents(s or "").lower())


def _loc(entry, practice=None):
    return {
        "practice": practice if practice is not None else entry.get("practice"),
        "street": entry.get("street"), "city": entry.get("city"), "region": entry.get("region"),
        "postal": entry.get("postal"), "country": entry["country"], "phone": entry.get("phone"),
        "precision": entry.get("location_precision", "city"), "sources": [entry["source"]["id"]],
    }


def _should_split(entry):
    ppl = entry["people"]
    if len(ppl) == 1:
        return True
    if not ppl:
        return False
    if entry["source"]["id"] == "bds_map":
        # map "Drs A, B, C" rows are mostly author lists or teams; split only short lists of full names
        return len(ppl) <= 3 and all(len(p["name"].split()) >= 2 for p in ppl)
    return len(ppl) <= 6


NOT_A_PERSON = re.compile(r"\b(doctors?|oncolog\w*|onclog\w*|several|clinic|hospital|cent(?:er|re)|university|institute|"
                         r"department|medical|health|radiation|radio-oncology|team|group|staff)\b", re.I)


def candidates(entries):
    out = []
    for e in entries:
        real = [p for p in e["people"] if not NOT_A_PERSON.search(p["name"])]
        if len(real) < len(e["people"]):
            # a facility or placeholder ("Several doctors") in the name field is not a clinician
            e = dict(e, people=real, practice=e.get("practice") or next(
                (p["name"] for p in e["people"] if re.search(r"[A-Z]\w+ \w", p["name"]) and NOT_A_PERSON.search(p["name"])
                 and not re.match(r"(?i)(several|oncology|radiation) ", p["name"])), None)
                or f"Clinic in {e.get('city') or 'unknown city'} (doctor not named)")
        locs = [_loc(e)] + [dict(_loc({**e, **{k: v for k, v in x.items() if v is not None},
                                       "location_precision": "street" if x.get("street") else "city"}),
                                 practice=x.get("practice") or e.get("practice")) for x in e["extra_locations"]]
        ev = "patient_reported" if e["source"]["kind"] == "patient_community" else "listed"
        base = {
            "specialty": e.get("specialty"), "locations": locs,
            "treatments": {f"{c}:{s}": [{"source": e["source"]["id"], "evidence": ev}] for c, s in e["treatments"]},
            "flags": set(e.get("flags") or []), "websites": [e["website"]] if e.get("website") else [],
            "emails": [e["email"]] if e.get("email") else [],
            "notes": [{"source": e["source"]["id"], "text": e["note"]}] if e.get("note") else [],
            "sources": [e["source"]],
        }
        if _should_split(e):
            others = [p["name"] for p in e["people"]]
            for p in e["people"]:
                c = dict(base, kind="clinician", name=p["name"], honorific=p.get("honorific"),
                         colleagues=[o for o in others if o != p["name"]])
                c["locations"] = [dict(l) for l in locs]
                c["flags"] = set(base["flags"])
                out.append(c)
        else:
            name = e.get("practice") or (", ".join(p["name"] for p in e["people"]) if e["people"] else None)
            if not name:
                continue
            out.append(dict(base, kind="practice", name=name, honorific=None,
                            colleagues=[p["name"] for p in e["people"]]))
    return out


def _regions(c):
    return {(l.get("region") or "").lower() for l in c["locations"]} - {""}


def _cities(c):
    return {_norm(l.get("city")) for l in c["locations"]} - {""}


def _compatible(a, b):
    if a["kind"] != b["kind"]:
        return False
    if {l["country"] for l in a["locations"]}.isdisjoint({l["country"] for l in b["locations"]}):
        return False
    if a["kind"] == "clinician":
        na, nb = a["name"].split(), b["name"].split()
        # surname-only records ("Dr Kelly") never merge with anything but the identical string
        if (len(na) == 1 or len(nb) == 1) and _norm(a["name"]) != _norm(b["name"]):
            return False
        if len(na) > 1 and len(nb) > 1 and _norm(na[0]) != _norm(nb[0]) and na[0][0].lower() != nb[0][0].lower():
            return False
    da, db = {_domain(u) for u in a["websites"]}, {_domain(u) for u in b["websites"]}
    if da & db - {None}:
        return True
    if _cities(a) & _cities(b) or _regions(a) & _regions(b):
        return True
    if not _regions(a) or not _regions(b):
        return True
    return False


def _same_loc(x, y):
    if x["country"] != y["country"]:
        return False
    if x.get("street") and y.get("street"):
        return _norm(x["street"])[:12] == _norm(y["street"])[:12] and _norm(x.get("city")) == _norm(y.get("city"))
    return _norm(x.get("city")) == _norm(y.get("city")) and (
        not x.get("practice") or not y.get("practice") or _norm(x["practice"])[:10] == _norm(y["practice"])[:10])


def _absorb(a, b):
    for l in b["locations"]:
        hit = next((m for m in a["locations"] if _same_loc(m, l)), None)
        if hit:
            for k in ("practice", "street", "postal", "phone", "region"):
                if not hit.get(k) and l.get(k):
                    hit[k] = l[k]
            if l.get("street"):
                hit["precision"] = "street"
            hit["sources"] = sorted(set(hit["sources"]) | set(l["sources"]))
        else:
            a["locations"].append(dict(l))
    for k, ev in b["treatments"].items():
        cur = a["treatments"].setdefault(k, [])
        for x in ev:
            if x not in cur:
                cur.append(x)
    a["flags"] |= b["flags"]
    for k in ("websites", "emails", "colleagues"):
        for v in b.get(k, []):
            if v not in a[k]:
                a[k].append(v)
    a["notes"] += [n for n in b["notes"] if n not in a["notes"]]
    a["sources"] += [s for s in b["sources"] if s not in a["sources"]]
    if not a.get("honorific") and b.get("honorific"):
        a["honorific"] = b["honorific"]
    if len(b["name"]) > len(a["name"]) and person_key(b["name"]) == person_key(a["name"]):
        a["name"] = b["name"]  # prefer the fuller spelling, e.g. with middle initial
    if not a.get("specialty") or (a["specialty"] == "hand_surgery" and b.get("specialty") not in (None, "hand_surgery")):
        a["specialty"] = b.get("specialty") or a.get("specialty")


def merge(cands):
    merged, index = [], {}
    for c in cands:
        if c["kind"] == "clinician":
            key = ("c", person_key(c["name"]))
        else:
            key = ("p", _norm(c["name"])[:24], _norm(c["locations"][0].get("city")))
        hit = next((m for m in index.get(key, []) if _compatible(m, c)), None)
        if hit:
            _absorb(hit, c)
        else:
            c = dict(c, colleagues=list(c.get("colleagues", [])), notes=list(c["notes"]),
                     sources=list(c["sources"]), websites=list(c["websites"]), emails=list(c["emails"]))
            merged.append(c)
            index.setdefault(key, []).append(c)
    # stable, readable ids
    seen = set()
    for m in merged:
        city = m["locations"][0].get("city") or m["locations"][0]["country"]
        base = slugify(f"{m['name']} {city}")
        sid, n = base, 2
        while sid in seen:
            sid, n = f"{base}-{n}", n + 1
        seen.add(sid)
        m["id"] = sid
        m["flags"] = sorted(m["flags"])
    return merged
