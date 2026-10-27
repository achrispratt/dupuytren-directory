"""Verify US clinicians against the CMS NPI Registry (NPPES).

A match tells us the doctor holds an active NPI, their specialty taxonomy, and their *current* practice address,
which matters because several patient-org lists are years old. We only accept a match when exactly one NPI record
fits the name, a relevant specialty, and (when we know it) the state.
"""
import re
import time

from lib import JsonCache, http_json, strip_accents

_cache = JsonCache("npi")
API = "https://npiregistry.cms.hhs.gov/api/"

RELEVANT = re.compile(
    r"orthop|hand surgery|plastic|radiation|radiology|podiat|foot|rheumat|dermatol|surgery|oncolog|"
    r"family|internal medicine|sports medicine|physical medicine|general practice",
    re.I,
)
SPECIALTY_FROM_TAXONOMY = [
    (re.compile(r"radiation oncology|radiation", re.I), "radiation_oncology"),
    (re.compile(r"podiatr|foot", re.I), "podiatry"),
    (re.compile(r"hand", re.I), "hand_surgery"),
    (re.compile(r"plastic", re.I), "plastic_surgery"),
    (re.compile(r"orthop", re.I), "orthopedic_surgery"),
    (re.compile(r"rheumat", re.I), "rheumatology"),
    (re.compile(r"dermat", re.I), "dermatology"),
]


def _query(first, last, state):
    key = f"{first}|{last}|{state or ''}"
    if key in _cache:
        return _cache.get(key)
    params = {"version": "2.1", "enumeration_type": "NPI-1", "last_name": last, "first_name": first, "limit": 50}
    if state:
        params["state"] = state
    try:
        res = http_json(API, params).get("results", [])
    except Exception as e:  # noqa: BLE001
        print("npi error", key, e)
        return None
    time.sleep(0.15)
    slim = []
    for r in res:
        b = r.get("basic", {})
        loc = next((a for a in r.get("addresses", []) if a.get("address_purpose") == "LOCATION"), {})
        tax = r.get("taxonomies", [])
        prim = next((t for t in tax if t.get("primary")), tax[0] if tax else {})
        slim.append({
            "npi": r.get("number"), "first": b.get("first_name"), "last": b.get("last_name"),
            "middle": b.get("middle_name"), "credential": b.get("credential"), "status": b.get("status"),
            "updated": b.get("last_updated"), "taxonomy": prim.get("desc"),
            "taxonomies": [t.get("desc") for t in tax],
            "address": {
                "street": " ".join(x for x in [loc.get("address_1"), loc.get("address_2")] if x),
                "city": loc.get("city"), "state": loc.get("state"), "postal": (loc.get("postal_code") or "")[:5],
                "phone": loc.get("telephone_number"),
            },
        })
    _cache.set(key, slim)
    return slim


def _name_parts(name):
    toks = [t for t in re.split(r"\s+", strip_accents(name).replace(".", " ")) if t]
    toks = [t for t in toks if t.lower() not in ("jr", "sr", "ii", "iii", "iv")]
    if len(toks) < 2:
        return None, None
    first = toks[0]
    if len(first) == 1 and len(toks) > 2:  # "C. Leland Rogers"
        first = toks[1]
    return first, toks[-1]


def _relevant(c):
    return any(RELEVANT.search(t or "") for t in c["taxonomies"])


def match(listing):
    if listing["kind"] != "clinician":
        return None
    states = sorted({l.get("region") for l in listing["locations"] if l["country"] == "US" and l.get("region")})
    if not any(l["country"] == "US" for l in listing["locations"]):
        return None
    first, last = _name_parts(listing["name"])
    if not first:
        return None
    pool = []
    for st in states or [None]:
        res = _query(first, last, st) or []
        pool += [c for c in res if _relevant(c)]
    if not pool and states:
        res = _query(first, last, None) or []
        pool = [c for c in res if _relevant(c)]
        if len({c["npi"] for c in pool}) != 1:
            return None
    uniq = {c["npi"]: c for c in pool}
    if len(uniq) != 1:
        return {"ambiguous": len(uniq)} if uniq else None
    return next(iter(uniq.values()))


def verify_all(listings):
    stats = {"checked": 0, "matched": 0, "ambiguous": 0}
    for m in listings:
        r = match(m)
        if r is None and m["kind"] == "clinician" and any(l["country"] == "US" for l in m["locations"]):
            stats["checked"] += 1
            m["npi"] = None
            continue
        if r is None:
            continue
        stats["checked"] += 1
        if "ambiguous" in r:
            stats["ambiguous"] += 1
            m["npi"] = {"ambiguous": r["ambiguous"]}
            continue
        stats["matched"] += 1
        m["npi"] = r
        for rx, spec in SPECIALTY_FROM_TAXONOMY:
            if any(rx.search(t or "") for t in r["taxonomies"]):
                m["npi_specialty"] = spec
                break
    _cache.save()
    print(f"npi: {stats}")
