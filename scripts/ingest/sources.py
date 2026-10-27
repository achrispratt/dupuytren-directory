"""Parse each source into uniform *entries*.

An entry is one listing as one source describes it:
  people: [{name, honorific}]   (empty for a clinic/department with no named doctor)
  practice, street, city, region, postal, country, phone, website, email
  treatments: [[code, site]], flags: [..], specialty, note
  source: {id, url, page_modified, label, kind}
  extra_locations: [{practice, street, city, region, postal, country, phone}]
"""
import glob
import html
import os
import re
import xml.etree.ElementTree as ET

from lib import DATA, clean_person, country_code, norm_url, region_code

SOURCE_LABELS = {
    "ids_rt_en": "International Dupuytren Society: radiotherapy clinics",
    "ids_rt_de": "International Dupuytren Society (German site): radiotherapy addresses",
    "ids_na_na": "International Dupuytren Society: needle aponeurotomy list, USA & Canada",
    "ids_na_uk": "International Dupuytren Society: needle aponeurotomy list, UK",
    "ids_na_world": "International Dupuytren Society: needle aponeurotomy list, other countries",
    "ids_na_de": "International Dupuytren Society (German site): needle fasciotomy addresses",
    "ids_cci_de": "International Dupuytren Society (German site): collagenase addresses",
    "ids_surgery_foot_de": "International Dupuytren Society (German site): Ledderhose surgery",
    "ids_cryo": "International Dupuytren Society: cryosurgery for Ledderhose",
    "bds_uk": "British Dupuytren's Society: UK & Ireland doctors and clinics",
    "bds_map": "British Dupuytren's Society: worldwide doctors map",
    "community": "Named repeatedly by patients on r/DupuytrenDisease, identity checked in the NPI registry",
}
SOURCE_KIND = {k: "patient_org_list" for k in SOURCE_LABELS}
SOURCE_KIND["community"] = "patient_community"


def _parse_tx(s):
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        code, _, site = part.partition(":")
        out.append([code.strip(), (site or "hand").strip()])
    return out


def _split_people(field):
    people = []
    for raw in [p for p in field.split(";") if p.strip()]:
        name, hon = clean_person(raw)
        if name:
            people.append({"name": name, "honorific": hon})
    return people


def parse_curated():
    entries = []
    for path in sorted(glob.glob(os.path.join(DATA, "curated", "*.txt"))):
        src = None
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith("@source"):
                kv = dict(re.findall(r"(\w+)=(\S+)", line))
                src = {
                    "id": kv["id"], "url": kv["url"], "page_modified": kv.get("page_modified"),
                    "label": SOURCE_LABELS[kv["id"]], "kind": SOURCE_KIND[kv["id"]],
                    "treatments": _parse_tx(kv.get("treatments", "")), "specialty": kv.get("specialty"),
                }
                continue
            cols = [c.strip() for c in line.split("|")]
            if line.startswith("+"):
                cols[0] = cols[0][1:].strip()
                cols += [""] * (7 - len(cols))
                prac, street, city, region, postal, cc, phone = cols[:7]
                cc = country_code(cc)
                entries[-1]["extra_locations"].append({
                    "practice": prac or None, "street": street or None, "city": city or None,
                    "region": region_code(region, cc), "postal": postal or None, "country": cc,
                    "phone": phone or None,
                })
                continue
            base, extra = cols[:11], cols[11:]
            base += [""] * (11 - len(base))
            people, prac, street, city, region, postal, cc, phone, web, email, note = base
            kv = {}
            for e in extra:
                if "=" in e:
                    k, _, v = e.partition("=")
                    kv[k.strip()] = v.strip()
            cc = country_code(cc)
            if not cc:
                raise ValueError(f"{path}:{lineno}: bad country")
            entries.append({
                "people": _split_people(people),
                "practice": prac or None, "street": street or None, "city": city or None,
                "region": region_code(region, cc), "postal": postal or None, "country": cc,
                "phone": phone or None, "website": norm_url(web), "email": email or None,
                "note": note or None,
                "treatments": _parse_tx(kv["tx"]) if "tx" in kv else [list(t) for t in src["treatments"]],
                "flags": [f for f in kv.get("flags", "").split(",") if f],
                "specialty": kv.get("specialty") or src["specialty"],
                "source": {k: src[k] for k in ("id", "url", "page_modified", "label", "kind")},
                "extra_locations": [],
                "location_precision": "street" if street else "city",
            })
    return entries


# --- British Dupuytren's Society worldwide map (Google My Maps KML) -------------------------------------------

BDS_LAYERS = {
    # layer (folder) name prefix -> (treatments, specialty)
    "Podiatrist V": ([["hyaluronidase_injection", "foot"], ["foot_care", "foot"]], "podiatry"),
    "Podiatrist": ([["foot_care", "foot"]], "podiatry"),
    "Hand Surgeon NA-X": ([["needle_aponeurotomy", "hand"], ["collagenase", "hand"]], "hand_surgery"),
    "Hand Surgeon NA": ([["needle_aponeurotomy", "hand"]], "hand_surgery"),
    "Hand Surgeon X": ([["collagenase", "hand"]], "hand_surgery"),
    "Hand Surgeon": ([["fasciectomy", "hand"]], "hand_surgery"),
    "RO": ([["radiotherapy", "hand"]], "radiation_oncology"),
}
GROUP_WORDS = re.compile(r"^(surgeons|unknown doctors|many different surgeons|all xpert clinics|clinical oncologist.*)$", re.I)
NS = "{http://www.opengis.net/kml/2.2}"


def _notes_to_tx(notes, foot_layer=False):
    n = notes.lower()
    tx, flags = [], []
    if "fasciectomy" in n or "surgery" in n:
        tx.append(["foot_surgery", "foot"] if foot_layer and "aponevrotomy" not in n else ["fasciectomy", "hand"])
    if re.search(r"\bna\b|aponevrotomy|aponeurotomy|pnf|needle", n):
        tx.append(["needle_aponeurotomy", "hand"])
    if "xiaflex" in n or "collagenase" in n or re.search(r"\band x\b", n):
        tx.append(["collagenase", "hand"])
    if "ledderhose" in n:
        flags.append("treats_ledderhose")
    if "rt friendly" in n:
        flags.append("rt_referral")
    if "paris" in n or "france" in n:
        flags.append("trained_paris")
    if "ultrasound" in n:
        flags.append("ultrasound_guided")
    if "physical therapy" in n or "conservative" in n:
        tx.append(["orthotics", "foot"] if foot_layer else ["hand_therapy", "hand"])
    return tx, flags


def _bds_people(title):
    t = html.unescape(title or "").strip()
    if not t or GROUP_WORDS.match(t):
        return [], True
    multi = bool(re.match(r"^(drs|profs|dres)\b", t, re.I)) or " and " in t.lower() or ";" in t \
        or t.count(",") >= 2 and not re.search(r"\b(md|m\.d\.|facs|frcsc)\b", t, re.I)
    if not multi:
        name, hon = clean_person(t)
        return ([{"name": name, "honorific": hon}] if name else []), False
    body = re.sub(r"^(drs|profs|dres)\.?\s+", "", t, flags=re.I)
    body = body.replace(" and others", "")
    parts = [p for p in re.split(r"\s*(?:;|,|\band\b|&)\s*", body) if p.strip()]
    people = []
    for p in parts:
        name, hon = clean_person(p)
        if name and len(name) > 1 and not re.fullmatch(r"[A-Z]\.?(\s*[A-Z]\.?)*", name):
            people.append({"name": name, "honorific": hon or "Dr"})
    return people, True


def parse_bds_map():
    root = ET.parse(os.path.join(DATA, "raw", "bds_map.kml")).getroot()
    url = "https://www.google.com/maps/d/viewer?mid=1nhuCG5DiGs6iSyvUrGN63jLZN-5TGug4"
    entries = []
    for folder in root.iter(NS + "Folder"):
        for pm in folder.findall(NS + "Placemark"):
            layer = (pm.findtext(NS + "name") or "").strip()
            d = {x.get("name"): (x.findtext(NS + "value") or "").strip() for x in pm.iter(NS + "Data")}
            title = d.get("Title") or d.get("Name") or ""
            people, is_group = _bds_people(title)
            key = next((k for k in BDS_LAYERS if layer.replace("Hand-Surgeon", "Hand Surgeon").startswith(k)), None)
            if layer in ("CO-rad",):
                key = "RO"
            if layer == "Foot/Ankle surgeons":
                tx, spec = [["foot_surgery", "foot"]], "foot_ankle_surgery"
            elif key:
                tx, spec = [list(t) for t in BDS_LAYERS[key][0]], BDS_LAYERS[key][1]
            else:
                continue
            notes = d.get("NOTES", "")
            ntx, flags = _notes_to_tx(notes, foot_layer=spec in ("podiatry", "foot_ankle_surgery"))
            for t in ntx:
                if t not in tx:
                    tx.append(t)
            cc = country_code(d.get("Country"))
            if not cc:
                continue
            region = d.get("Region") or None
            if cc == "GB" and region and region.lower() in ("scotland", "wales", "northern ireland"):
                pass
            addr = (d.get("Address") or d.get("Adress") or "").strip()
            note = notes.strip() or None
            # a few sheets put free text in the address column
            if addr and not re.search(r"\d", addr) and len(addr.split()) > 3:
                note = "; ".join(x for x in [note, addr] if x)
                addr = ""
            practice = (d.get("Practice Name") or d.get("Clinic") or "").strip() or None
            if practice and practice.lower().startswith("http"):
                practice = None
            if practice and practice.lower() in ("podiatrist",):
                practice = None
            if is_group and not people and not practice:
                practice = html.unescape(title).strip() or None
            if layer == "CO-rad" and not people and not practice:
                practice = "Clinical oncology (NHS radiotherapy)"
            entries.append({
                "people": people, "group": is_group and len(people) != 1,
                "practice": practice, "street": addr or None, "city": (d.get("City") or "").strip() or None,
                "region": region_code(region, cc), "postal": (d.get("Code") or "").strip() or None,
                "country": cc, "phone": None, "website": norm_url(d.get("Website") or d.get("website")),
                "email": None, "note": note, "treatments": tx, "flags": flags, "specialty": spec,
                "source": {"id": "bds_map", "url": url, "page_modified": None,
                           "label": "British Dupuytren's Society: worldwide doctors map", "kind": "patient_org_list",
                           "layer": layer},
                "extra_locations": [],
                "location_precision": "street" if addr else "city",
            })
    return entries


if __name__ == "__main__":
    import collections
    c = parse_curated()
    b = parse_bds_map()
    print(len(c), "curated entries;", len(b), "BDS map entries")
    print(collections.Counter(e["source"]["id"] for e in c + b))
    for e in b[:5] + [x for x in b if x.get("group")][:8]:
        print(e["people"], e["practice"], e["city"], e["country"], e["treatments"], e["flags"])
