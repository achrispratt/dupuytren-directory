"""Turn enriched listings into the published dataset (data/build/directory.json).

Every treatment claim keeps its evidence trail. Evidence strength, strongest first:
  listed             a patient organisation (IDS/BDS) lists the clinician for this treatment
  trial_site         an open ClinicalTrials.gov study of this treatment runs here
  trial_investigator the clinician is a named investigator on a study of this treatment
  patient_reported   a patient on r/DupuytrenDisease names the clinician alongside this treatment
  inferred           derived from a source's general statement (e.g. BDS: RT clinics usually treat Ledderhose too)
"""
import datetime
import json
import os
import re

from lib import COUNTRY_NAMES, TREATMENTS
from sources import SOURCE_LABELS

EVIDENCE_RANK = {"listed": 0, "trial_site": 1, "trial_investigator": 2, "patient_reported": 3, "inferred": 4}
EARLY = {"radiotherapy", "steroid_injection", "hyaluronidase_injection"}
STALE_RX = re.compile(r"no longer practi|doesn.t practi|retired|not (yet )?confirmed|may have moved", re.I)
SPECIALTY_LABELS = {
    "hand_surgery": "Hand surgeon", "orthopedic_surgery": "Orthopaedic surgeon", "plastic_surgery": "Plastic surgeon",
    "radiation_oncology": "Radiation oncologist", "podiatry": "Podiatrist", "foot_ankle_surgery": "Foot & ankle surgeon",
    "rheumatology": "Rheumatologist", "dermatology": "Dermatologist", "general_practice": "GP",
    "research": "Research site", "sports_medicine": "Sports medicine physician",
}
EXTRA_SOURCES = {
    "ctgov": ("ClinicalTrials.gov", "https://clinicaltrials.gov/", "registry"),
    "reddit": ("r/DupuytrenDisease (via the Arctic Shift archive)", "https://www.reddit.com/r/DupuytrenDisease/", "community"),
    "npi": ("CMS NPI Registry", "https://npiregistry.cms.hhs.gov/", "registry"),
    "pubmed": ("PubMed", "https://pubmed.ncbi.nlm.nih.gov/", "literature"),
}


def _treatments(m):
    tx = dict(m["treatments"])
    has_foot_rt = "radiotherapy:foot" in tx
    if "radiotherapy:hand" in tx and not has_foot_rt:
        tx["radiotherapy:foot"] = [{"source": "bds_uk", "evidence": "inferred",
                                    "note": "BDS: clinics that treat Dupuytren's with RT are likely to treat Ledderhose as well"}]
    out = []
    for key, evs in tx.items():
        code, site = key.split(":")
        if code not in TREATMENTS:
            continue
        evs = sorted(evs, key=lambda e: EVIDENCE_RANK.get(e["evidence"], 9))
        out.append({"code": code, "site": site, "best": evs[0]["evidence"], "evidence": evs})
    out.sort(key=lambda t: (t["site"], EVIDENCE_RANK[t["best"]], t["code"]))
    return out


def _verification(m, independent):
    reasons, warn = [], []
    if m.get("npi") and m["npi"].get("npi"):
        reasons.append(f"Active NPI {m['npi']['npi']} ({m['npi'].get('taxonomy') or 'specialty unknown'})")
    if len(independent) >= 2:
        reasons.append(f"Listed by {len(independent)} independent patient organisations")
    if m.get("trials"):
        reasons.append(f"Named on {len(m['trials'])} ClinicalTrials.gov stud{'y' if len(m['trials']) == 1 else 'ies'}")
    if m.get("reddit", {}).get("count"):
        reasons.append(f"Mentioned by patients {m['reddit']['count']}× on r/DupuytrenDisease")
    for n in m["notes"]:
        if STALE_RX.search(n["text"]):
            warn.append(n["text"])
    if any(s["id"] == "ids_na_uk" for s in m["sources"]) and len(m["sources"]) == 1:
        warn.append("Only source is a UK list last updated in 2017")
    is_us_clin = m["kind"] == "clinician" and any(l["country"] == "US" for l in m["locations"])
    if is_us_clin and "npi" in m and not (m["npi"] or {}).get("npi"):
        warn.append("No unique match in the US NPI registry (name may be incomplete, or the doctor may have retired)")
    npi_ok = bool((m.get("npi") or {}).get("npi"))
    if warn and not reasons:
        level = "needs_review"
    elif all(s["kind"] == "patient_community" for s in m["sources"]):
        level = "listed"  # a registry confirms who they are, but no organisation lists them yet
    elif not warn and (npi_ok or len(independent) >= 2 or m["kind"] == "trial_site"):
        level = "corroborated"
    else:
        level = "listed"
    return level, reasons, warn


def run(listings, build_dir):
    today = datetime.date.today().isoformat()
    trials = json.load(open(os.path.join(build_dir, "trials.json"))) if os.path.exists(
        os.path.join(build_dir, "trials.json")) else []
    sources = {}
    out = []
    for m in listings:
        if not any(l.get("lat") is not None for l in m["locations"]):
            # keep it, but it won't show on the map or in distance search
            pass
        independent = {("ids" if s["id"].startswith("ids") else "bds" if s["id"].startswith("bds") else s["id"])
                       for s in m["sources"] if s["kind"] == "patient_org_list"}
        for s in m["sources"]:
            sources.setdefault(s["id"], {"id": s["id"], "label": s["label"], "url": s["url"], "kind": s["kind"],
                                         "page_modified": s.get("page_modified")})
        tx = _treatments(m)
        level, reasons, warn = _verification(m, independent)
        flags = set(m["flags"])
        if any(t["code"] in EARLY and t["best"] != "inferred" for t in tx) or "early_stage" in flags:
            flags.add("early_stage")
        conditions = sorted({"dupuytren" if t["site"] == "hand" else "ledderhose" for t in tx
                             if t["best"] != "inferred"} | ({"ledderhose"} if "treats_ledderhose" in flags else set()))
        npi = m.get("npi") if (m.get("npi") or {}).get("npi") else None
        specialty = m.get("npi_specialty") or m.get("specialty")
        locs = []
        for l in m["locations"]:
            locs.append({k: l.get(k) for k in ("practice", "street", "city", "region", "postal", "country", "phone",
                                                 "lat", "lng", "geo_precision")})
        if npi and npi.get("address", {}).get("street"):
            a = npi["address"]
            if not any((l.get("postal") or "")[:5] == a["postal"] for l in locs):
                locs.append({"practice": "Current practice address (NPI registry)", "street": a["street"].title(),
                             "city": (a["city"] or "").title(), "region": a["state"], "postal": a["postal"],
                             "country": "US", "phone": a.get("phone"), "lat": None, "lng": None,
                             "geo_precision": None, "from_npi": True})
        out.append({
            "id": m["id"], "kind": m["kind"], "name": m["name"], "honorific": m.get("honorific"),
            "credential": (npi or {}).get("credential"),
            "specialty": specialty, "specialty_label": SPECIALTY_LABELS.get(specialty, specialty),
            "colleagues": m.get("colleagues", []), "locations": locs,
            "countries": sorted({l["country"] for l in locs}),
            "website": (m["websites"] or [None])[0], "websites": m["websites"], "emails": m["emails"],
            "treatments": tx, "conditions": conditions, "flags": sorted(flags),
            "early_stage": "early_stage" in flags,
            "verification": {"level": level, "reasons": reasons, "warnings": warn, "checked": today},
            "npi": npi, "publications": m.get("publications"), "reddit": m.get("reddit"),
            "trials": m.get("trials", []), "notes": m["notes"],
            "sources": [{"id": s["id"], "url": s["url"], "layer": s.get("layer")} for s in m["sources"]],
        })
    for k, (label, url, kind) in EXTRA_SOURCES.items():
        sources.setdefault(k, {"id": k, "label": label, "url": url, "kind": kind, "page_modified": None})
    for sid, label in SOURCE_LABELS.items():
        if sid in sources:
            sources[sid]["label"] = label
    doc = {
        "generated_at": today,
        "treatments": [{"code": k, "label": v} for k, v in TREATMENTS.items()],
        "countries": COUNTRY_NAMES,
        "sources": sorted(sources.values(), key=lambda s: s["id"]),
        "listings": sorted(out, key=lambda x: x["id"]),
        "trials": trials,
    }
    json.dump(doc, open(os.path.join(build_dir, "directory.json"), "w"), ensure_ascii=False, indent=1)
    lv = {}
    for x in out:
        lv[x["verification"]["level"]] = lv.get(x["verification"]["level"], 0) + 1
    print(f"finalize: {len(out)} listings, {len(trials)} trials, verification {lv}")
