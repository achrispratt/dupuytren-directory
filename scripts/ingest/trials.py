"""ClinicalTrials.gov: Dupuytren's / Ledderhose studies, their sites and investigators.

* Writes data/build/trials.json for the site's trials section (all studies, plain fields).
* Adds open trial sites (recruiting / not yet recruiting) as listings, so patients near a site can find them.
* Tags existing listings whose clinician is a named investigator ("trial_investigator" evidence).
"""
import json
import os
import re

from lib import COUNTRIES, http_json, person_key, region_code, slugify, clean_person

API = "https://clinicaltrials.gov/api/v2/studies"
QUERY = 'Dupuytren OR Ledderhose OR "plantar fibromatosis" OR "palmar fibromatosis"'
OPEN = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}
ACTIVE = OPEN | {"ACTIVE_NOT_RECRUITING"}


def _interventions_to_tx(names, ledderhose):
    site = "foot" if ledderhose else "hand"
    text = " ".join(names).lower()
    tx = []
    for pat, code in [
        (r"radiat|radiother|\brt\b|x-ray|electron", "radiotherapy"),
        (r"collagenase|xiaflex|xiapex|cnt201|cch\b", "collagenase"),
        (r"needle|percutaneous|aponeurotomy|fasciotomy", "needle_aponeurotomy"),
        (r"triamcinolone|steroid|cortico|kenalog", "steroid_injection"),
        (r"fasciectomy", "fasciectomy"),
        (r"fat graft|lipofill|lipograft", "lipofilling"),
    ]:
        if re.search(pat, text):
            tx.append([code, site])
    return tx


def fetch():
    studies, token = [], None
    while True:
        params = {"query.cond": QUERY, "pageSize": 200, "countTotal": "true"}
        if token:
            params["pageToken"] = token
        res = http_json(API, params)
        studies += res["studies"]
        token = res.get("nextPageToken")
        if not token:
            return studies


def _slim(s):
    p = s["protocolSection"]
    ident, status = p["identificationModule"], p["statusModule"]
    conds = p.get("conditionsModule", {}).get("conditions", [])
    ints = [i.get("name", "") for i in p.get("armsInterventionsModule", {}).get("interventions", [])]
    cl = p.get("contactsLocationsModule", {})
    ledd = bool(re.search(r"ledderhose|plantar", " ".join(conds + [ident.get("briefTitle", "")]), re.I))
    design = p.get("designModule", {})
    return {
        "nct_id": ident["nctId"],
        "title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "status": status.get("overallStatus"),
        "start": (status.get("startDateStruct") or {}).get("date"),
        "completion": (status.get("primaryCompletionDateStruct") or status.get("completionDateStruct") or {}).get("date"),
        "updated": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
        "phases": design.get("phases", []),
        "study_type": design.get("studyType"),
        "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
        "conditions": conds,
        "condition_site": "foot" if ledd else "hand",
        "interventions": ints,
        "treatments": _interventions_to_tx(ints, ledd),
        "sponsor": (p.get("sponsorCollaboratorsModule", {}).get("leadSponsor") or {}).get("name"),
        "summary": (p.get("descriptionModule") or {}).get("briefSummary"),
        "eligibility": {
            "min_age": p.get("eligibilityModule", {}).get("minimumAge"),
            "max_age": p.get("eligibilityModule", {}).get("maximumAge"),
        },
        "officials": [{"name": o.get("name"), "affiliation": o.get("affiliation"), "role": o.get("role")}
                      for o in cl.get("overallOfficials", [])],
        "central_contacts": [{"name": c.get("name"), "phone": c.get("phone"), "email": c.get("email")}
                             for c in cl.get("centralContacts", [])],
        "locations": [{
            "facility": l.get("facility"), "city": l.get("city"), "state": l.get("state"), "zip": l.get("zip"),
            "country": l.get("country"), "status": l.get("status"),
            "lat": (l.get("geoPoint") or {}).get("lat"), "lng": (l.get("geoPoint") or {}).get("lon"),
            "contacts": [{"name": c.get("name"), "role": c.get("role"), "phone": c.get("phone"), "email": c.get("email")}
                         for c in l.get("contacts", [])],
        } for l in cl.get("locations", [])],
        "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
    }


def run(listings, build_dir):
    trials = [_slim(s) for s in fetch()]
    trials.sort(key=lambda t: (t["status"] not in ACTIVE, t["status"] not in OPEN, t["start"] or ""), reverse=False)
    json.dump(trials, open(os.path.join(build_dir, "trials.json"), "w"), ensure_ascii=False, indent=1)

    by_key = {}
    for m in listings:
        if m["kind"] == "clinician":
            by_key.setdefault(person_key(m["name"]), []).append(m)

    tagged = 0
    for t in trials:
        people = [o["name"] for o in t["officials"]] + [c["name"] for l in t["locations"] for c in l["contacts"]
                                                         if c.get("role") in ("PRINCIPAL_INVESTIGATOR", "SUB_INVESTIGATOR")]
        for raw in filter(None, people):
            name, _ = clean_person(raw)
            for m in by_key.get(person_key(name), []):
                m.setdefault("trials", [])
                if t["nct_id"] not in [x["nct_id"] for x in m["trials"]]:
                    m["trials"].append({"nct_id": t["nct_id"], "title": t["title"], "status": t["status"]})
                    tagged += 1
                for code, site in t["treatments"]:
                    ev = {"source": "ctgov", "evidence": "trial_investigator", "ref": t["nct_id"]}
                    cur = m["treatments"].setdefault(f"{code}:{site}", [])
                    if ev not in cur:
                        cur.append(ev)

    # open sites become listings
    existing = {m["id"] for m in listings}
    added = 0
    for t in trials:
        if t["status"] not in OPEN:
            continue
        for l in t["locations"]:
            if l.get("status") and l["status"] not in OPEN:
                continue
            cc = COUNTRIES.get((l.get("country") or "").lower())
            if not cc:
                continue
            pi = next((c["name"] for c in l["contacts"] if c.get("role") == "PRINCIPAL_INVESTIGATOR"), None)
            lid = slugify(f"trial {l.get('facility')} {l.get('city')}")
            hit = next((m for m in listings if m["id"] == lid), None)
            tx = {f"{c}:{s}": [{"source": "ctgov", "evidence": "trial_site", "ref": t["nct_id"]}] for c, s in t["treatments"]}
            tx.setdefault(f"clinical_trial:{t['condition_site']}", []).append(
                {"source": "ctgov", "evidence": "trial_site", "ref": t["nct_id"]})
            if hit:
                for k, v in tx.items():
                    hit["treatments"].setdefault(k, []).extend(x for x in v if x not in hit["treatments"].get(k, []))
                if t["nct_id"] not in [x["nct_id"] for x in hit.setdefault("trials", [])]:
                    hit["trials"].append({"nct_id": t["nct_id"], "title": t["title"], "status": t["status"]})
                continue
            contact = next((c for c in l["contacts"] if c.get("phone") or c.get("email")), None) or \
                next((c for c in t["central_contacts"] if c.get("phone") or c.get("email")), None) or {}
            listings.append({
                "id": lid, "kind": "trial_site", "name": l.get("facility") or "Trial site", "honorific": None,
                "colleagues": [clean_person(pi)[0]] if pi else [],
                "specialty": "research",
                "locations": [{
                    "practice": l.get("facility"), "street": None, "city": l.get("city"),
                    "region": region_code(l.get("state"), cc), "postal": l.get("zip"), "country": cc,
                    "phone": contact.get("phone"), "precision": "city", "sources": ["ctgov"],
                    "lat": l.get("lat"), "lng": l.get("lng"), "geo_precision": "city" if l.get("lat") else None,
                }],
                "treatments": tx, "flags": ["clinical_trial"], "websites": [t["url"]],
                "emails": [contact["email"]] if contact.get("email") else [],
                "notes": [{"source": "ctgov", "text": f"Recruiting site for {t['nct_id']}: {t['title']}"}],
                "sources": [{"id": "ctgov", "url": t["url"], "page_modified": t["updated"],
                             "label": "ClinicalTrials.gov", "kind": "registry"}],
                "trials": [{"nct_id": t["nct_id"], "title": t["title"], "status": t["status"]}],
            })
            existing.add(lid)
            added += 1
    print(f"trials: {len(trials)} studies ({sum(t['status'] in OPEN for t in trials)} open); "
          f"{tagged} investigator links; {added} trial-site listings added")
