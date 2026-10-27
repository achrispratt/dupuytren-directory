"""Shared helpers for the ingestion pipeline: names, countries, regions, treatment vocabulary."""
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
UA = "dupuytren-directory/0.1 (patient-run directory; contact via GitHub achrispratt/dupuytren-directory)"

# Treatment vocabulary. A listing offers a treatment for a body site ("hand" = Dupuytren's, "foot" = Ledderhose).
TREATMENTS = {
    "radiotherapy": "Radiation therapy (low-dose RT)",
    "steroid_injection": "Steroid injection",
    "needle_aponeurotomy": "Needle aponeurotomy (PNF / needle release)",
    "collagenase": "Collagenase injection (Xiaflex)",
    "fasciectomy": "Fasciectomy (open surgery)",
    "dermofasciectomy": "Dermofasciectomy (surgery with skin graft)",
    "lipofilling": "Needle release with fat grafting (PALF)",
    "hyaluronidase_injection": "Hyaluronidase injection (Vitrase)",
    "cryoablation": "Cryoablation (cryosurgery)",
    "shockwave": "Shockwave therapy (ESWT)",
    "foot_surgery": "Plantar fibroma / plantar fasciectomy surgery",
    "orthotics": "Orthotics and offloading insoles",
    "foot_care": "Ledderhose foot care (podiatry)",
    "ultrasound_diagnosis": "Ultrasound diagnosis",
    "hand_therapy": "Hand therapy, splinting, physio",
    "clinical_trial": "Clinical trial site",
}
SITES = ("hand", "foot")

COUNTRIES = {
    "usa": "US", "us": "US", "united states": "US", "canada": "CA", "uk": "GB", "great britain": "GB",
    "united kingdom": "GB", "england": "GB", "scotland": "GB", "wales": "GB", "ireland": "IE", "australia": "AU",
    "new zealand": "NZ", "germany": "DE", "austria": "AT", "vienna": "AT", "switzerland": "CH", "france": "FR",
    "belgium": "BE", "begium": "BE", "the netherlands": "NL", "netherlands": "NL", "nederland": "NL", "spain": "ES",
    "portugal": "PT", "italy": "IT", "denmark": "DK", "sweden": "SE", "norway": "NO", "finland": "FI",
    "poland": "PL", "hungary": "HU", "romania": "RO", "bulgaria": "BG", "slovenia": "SI", "lithuania": "LT",
    "moldova": "MD", "russia": "RU", "turkey": "TR", "cyprus": "CY", "israel": "IL", "iran": "IR", "iraq": "IQ",
    "saudi-arabia": "SA", "saudi arabia": "SA", "united arab emirates": "AE", "india": "IN",
    "jammu and kashmir": "IN", "pakistan": "PK", "bangladesh": "BD", "nepal": "NP", "china": "CN",
    "hong kong": "HK", "japan": "JP", "korea": "KR", "south korea": "KR", "thailand": "TH", "malaysia": "MY",
    "singapore": "SG", "indonesia": "ID", "brazil": "BR", "brasil": "BR", "argentina": "AR", "chile": "CL",
    "chili": "CL", "colombia": "CO", "peru": "PE", "mexico": "MX", "south africa": "ZA", "soutn africa": "ZA",
    "namibia": "NA", "kenya": "KE", "senegal": "SN", "morocco": "MA", "marocco": "MA",
}
COUNTRY_NAMES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "IE": "Ireland", "AU": "Australia",
    "NZ": "New Zealand", "DE": "Germany", "AT": "Austria", "CH": "Switzerland", "FR": "France", "BE": "Belgium",
    "NL": "Netherlands", "ES": "Spain", "PT": "Portugal", "IT": "Italy", "DK": "Denmark", "SE": "Sweden",
    "NO": "Norway", "FI": "Finland", "PL": "Poland", "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria",
    "SI": "Slovenia", "LT": "Lithuania", "MD": "Moldova", "RU": "Russia", "TR": "Turkey", "CY": "Cyprus",
    "IL": "Israel", "IR": "Iran", "IQ": "Iraq", "SA": "Saudi Arabia", "AE": "United Arab Emirates", "IN": "India",
    "PK": "Pakistan", "BD": "Bangladesh", "NP": "Nepal", "CN": "China", "HK": "Hong Kong", "JP": "Japan",
    "KR": "South Korea", "TH": "Thailand", "MY": "Malaysia", "SG": "Singapore", "ID": "Indonesia", "BR": "Brazil",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru", "MX": "Mexico", "ZA": "South Africa",
    "NA": "Namibia", "KE": "Kenya", "SN": "Senegal", "MA": "Morocco", "TW": "Taiwan", "GR": "Greece",
    "CZ": "Czechia", "EG": "Egypt", "IS": "Iceland", "EE": "Estonia", "LV": "Latvia", "HR": "Croatia",
    "RS": "Serbia", "SK": "Slovakia", "UA": "Ukraine", "LU": "Luxembourg",
}

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR",
}
CA_PROVINCES = {
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB",
    "newfoundland and labrador": "NL", "newfoundland": "NL", "nova scotia": "NS", "ontario": "ON",
    "prince edward island": "PE", "quebec": "QC", "québec": "QC", "saskatchewan": "SK",
}


def country_code(raw):
    if not raw:
        return None
    s = raw.strip()
    if s.upper() == "UK":
        return "GB"
    if len(s) == 2 and s.isupper():
        return s
    return COUNTRIES.get(s.lower())


def region_code(region, cc):
    if not region:
        return None
    r = region.strip().strip(",")
    low = r.lower()
    if cc == "US":
        if len(r) == 2 and r.upper() in US_STATES.values():
            return r.upper()
        return US_STATES.get(low, r.title() if r.isupper() else r)
    if cc == "CA":
        if len(r) == 2:
            return r.upper()
        return CA_PROVINCES.get(low, r)
    return r


TITLE_RE = re.compile(
    r"^(?:(?:dr\.?|dra\.?|drs\.?|prof\.?|professor|doctor|mr\.?|mrs\.?|ms\.?|miss|pd|priv\.?-?doz\.?|"
    r"privatdozent|chefarzt|oa|primarius|doz\.?|assist\.?|asst\.?|assoc\.?|associate|assistant|clinical)\s+)+",
    re.I,
)
CRED_RE = re.compile(
    r",?\s*\b(?:m\.?d\.?|d\.?o\.?|dpm|phd|ph\.d\.?|mph|ms|m\.s\.|facs|faaos|frcs[a-z()]*|frcsc|fracs(?:\s*\(plast\))?|"
    r"mbbs(?:\s*\(hons\))?|mb\s*bs|mb|bsc|msc|facro|chs|dr\.?)\b\.?",
    re.I,
)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def clean_person(raw):
    """Turn 'Dr. Prosper Benhaim (CHS)' / 'Smith, Maggi' / 'William B Ericson Jr MD FACS' into display name + honorific."""
    s = re.sub(r"\(.*?\)", "", raw or "").strip()
    s = re.sub(r"\*+.*$", "", s).strip()
    m = re.match(r"^(Dr\.?|Dra\.?|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss|PD|Priv\.?-?Doz\.?)\b", s, re.I)
    honorific = None
    if m:
        h = m.group(1).rstrip(".").lower()
        honorific = {"dr": "Dr", "dra": "Dr", "prof": "Prof", "professor": "Prof", "mr": "Mr", "mrs": "Mrs",
                     "ms": "Ms", "miss": "Miss", "pd": "PD Dr", "priv.-doz": "PD Dr", "privdoz": "PD Dr",
                     "priv-doz": "PD Dr"}.get(h, m.group(1))
    s = TITLE_RE.sub("", s)
    s = re.sub(r"^(?:dr\.?|prof\.?)\s+", "", s, flags=re.I)
    # trailing ", Dr." (Mexican entries)
    s = re.sub(r",\s*dr\.?$", "", s, flags=re.I)
    prev = None
    while prev != s:
        prev = s
        s = CRED_RE.sub("", s).strip().strip(",").strip()
    # "Last, First" -> "First Last"
    if s.count(",") == 1:
        a, b = [p.strip() for p in s.split(",")]
        if a and b and " " not in a and len(b.split()) <= 2:
            s = f"{b} {a}"
    s = re.sub(r"\s+", " ", s).strip(" .;")
    if s.isupper() and len(s) > 3:
        s = s.title()
    return s, honorific


def person_key(name):
    """Dedup key: ascii-folded 'firstinitial lastname'. Middle names and initials are ignored."""
    s = strip_accents(name).lower()
    s = re.sub(r"[^a-z\s'-]", " ", s)
    toks = [t for t in s.split() if t not in ("jr", "sr", "ii", "iii", "iv", "von", "van", "de", "der", "den", "la", "le")]
    if not toks:
        return None
    last = toks[-1].replace("'", "").replace("-", "")
    first = toks[0][0] if len(toks) > 1 else ""
    return f"{first} {last}".strip()


def slugify(s):
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80]


def norm_url(u):
    if not u:
        return None
    u = u.strip().rstrip(".")
    if u.lower().startswith("www."):
        u = "https://" + u
    if not re.match(r"^https?://", u, re.I):
        if re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", u, re.I):
            u = "https://" + u
        else:
            return None
    return u


def http_json(url, params=None, headers=None, retries=4, sleep=1.0):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - network flakiness, retry with backoff
            last = e
            time.sleep(sleep * (2 ** i))
    raise last


class JsonCache:
    """A tiny on-disk cache so re-running the pipeline doesn't re-hit public APIs."""

    def __init__(self, name):
        os.makedirs(CACHE, exist_ok=True)
        self.path = os.path.join(CACHE, name + ".json")
        self.data = json.load(open(self.path)) if os.path.exists(self.path) else {}
        self.dirty = 0

    def get(self, k):
        return self.data.get(k)

    def __contains__(self, k):
        return k in self.data

    def set(self, k, v):
        self.data[k] = v
        self.dirty += 1
        if self.dirty % 25 == 0:
            self.save()

    def save(self):
        tmp = self.path + ".tmp"
        json.dump(self.data, open(tmp, "w"), ensure_ascii=False, indent=0, sort_keys=True)
        os.replace(tmp, self.path)
