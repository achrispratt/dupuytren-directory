"""Geocode listing locations.

US street addresses go to the US Census geocoder (free, no key, accurate). Everything else goes to OpenStreetMap
Nominatim (structured search, 1 request/second per its usage policy), falling back from street -> postcode -> city.
Results are cached in data/cache/geocode.json so reruns are instant.
"""
import re
import time

from lib import COUNTRY_NAMES, JsonCache, http_json

_cache = JsonCache("geocode")
_last = [0.0]


def _nominatim(params):
    key = "nom|" + "|".join(f"{k}={v}" for k, v in sorted(params.items()))
    if key in _cache:
        return _cache.get(key)
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        res = http_json("https://nominatim.openstreetmap.org/search",
                        dict(params, format="jsonv2", limit=1, addressdetails=0))
    except Exception as e:  # noqa: BLE001
        print("nominatim error", params, e)
        return None
    hit = None
    if res:
        r = res[0]
        hit = {"lat": float(r["lat"]), "lng": float(r["lon"]), "label": r.get("display_name"),
               "type": r.get("addresstype") or r.get("type")}
    _cache.set(key, hit)
    return hit


def _census(street, city, state, postal):
    one = ", ".join(x for x in [street, city, state, postal] if x)
    key = "census|" + one
    if key in _cache:
        return _cache.get(key)
    try:
        res = http_json("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                        {"address": one, "benchmark": "Public_AR_Current", "format": "json"})
        m = res["result"]["addressMatches"]
    except Exception as e:  # noqa: BLE001
        print("census error", one, e)
        return None
    hit = None
    if m:
        hit = {"lat": m[0]["coordinates"]["y"], "lng": m[0]["coordinates"]["x"], "label": m[0]["matchedAddress"],
               "type": "address"}
    _cache.set(key, hit)
    return hit


def _clean_street(s):
    s = re.sub(r"(,\s*)?\b(suite|ste\.?|unit|level|building|bldg\.?|floor|fl\.?)\s*[\w-]+", "", s, flags=re.I)
    s = re.sub(r"#\s*[\w-]+", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,;")


def geocode(loc):
    cc = loc["country"]
    street, city, region, postal = loc.get("street"), loc.get("city"), loc.get("region"), loc.get("postal")
    if cc == "US" and street and city:
        hit = _census(street, city, region, postal)
        if hit:
            return hit, "street"
    tries = []
    if street and city:
        tries.append(({"street": _clean_street(street), "city": city, "postalcode": postal or "", "countrycodes": cc.lower()}, "street"))
    if postal:
        tries.append(({"postalcode": postal, "countrycodes": cc.lower()}, "postal"))
    if city:
        q = {"city": city, "countrycodes": cc.lower()}
        if region and cc in ("US", "CA", "AU"):
            q["state"] = region
        tries.append((q, "city"))
        tries.append(({"q": ", ".join(x for x in [city, region, COUNTRY_NAMES.get(cc, cc)] if x)}, "city"))
    if loc.get("practice"):
        tries.append(({"q": ", ".join(x for x in [loc["practice"], city, COUNTRY_NAMES.get(cc, cc)] if x)}, "practice"))
    if region:
        tries.append(({"q": f"{region}, {COUNTRY_NAMES.get(cc, cc)}"}, "region"))
    for params, precision in tries:
        params = {k: v for k, v in params.items() if v}
        hit = _nominatim(params)
        if hit:
            if precision == "practice":
                precision = "street" if hit.get("type") not in ("city", "town", "village", "county", "state") else "city"
            return hit, precision
    return None, None


def geocode_all(listings, log_every=50):
    n = 0
    for m in listings:
        for loc in m["locations"]:
            if loc.get("lat") is not None:
                continue
            hit, precision = geocode(loc)
            n += 1
            if hit:
                loc["lat"], loc["lng"], loc["geo_precision"] = round(hit["lat"], 6), round(hit["lng"], 6), precision
            if n % log_every == 0:
                print(f"  geocoded {n} locations", flush=True)
                _cache.save()
    _cache.save()
