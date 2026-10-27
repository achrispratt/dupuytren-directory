"""Build the directory dataset.

  python3 scripts/ingest/build.py            # all stages
  python3 scripts/ingest/build.py merge geocode

Stages:
  merge     parse curated lists + BDS map, merge into listings          -> data/build/listings.json
  geocode   add lat/lng to every location (cached)
  npi       verify US clinicians against the CMS NPI Registry (cached)
  trials    add ClinicalTrials.gov Dupuytren/Ledderhose studies + sites  -> data/build/trials.json
  pubmed    count Dupuytren/Ledderhose publications per clinician (cached)
  reddit    find r/DupuytrenDisease mentions via the Arctic Shift archive (cached)
  finalize  derive verification status, early-stage flag, search text   -> data/build/directory.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib import DATA  # noqa: E402

BUILD = os.path.join(DATA, "build")
LISTINGS = os.path.join(BUILD, "listings.json")


def load():
    return json.load(open(LISTINGS))


def save(listings):
    os.makedirs(BUILD, exist_ok=True)
    tmp = LISTINGS + ".tmp"
    json.dump(listings, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, LISTINGS)


def stage_merge():
    from merge import candidates, merge
    from sources import parse_bds_map, parse_curated
    entries = parse_curated() + parse_bds_map()
    listings = merge(candidates(entries))
    save(listings)
    print(f"merge: {len(entries)} source entries -> {len(listings)} listings")


def stage_geocode():
    from geocode import geocode_all
    listings = load()
    geocode_all(listings)
    save(listings)
    locs = [l for m in listings for l in m["locations"]]
    print(f"geocode: {sum(1 for l in locs if l.get('lat') is not None)}/{len(locs)} locations placed")


def stage_npi():
    from npi import verify_all
    listings = load()
    verify_all(listings)
    save(listings)


def stage_trials():
    from trials import run
    listings = load()
    run(listings, BUILD)
    save(listings)


def stage_pubmed():
    from pubmed import run
    listings = load()
    run(listings)
    save(listings)


def stage_reddit():
    from reddit import run
    listings = load()
    run(listings)
    save(listings)


def stage_finalize():
    from finalize import run
    run(load(), BUILD)


STAGES = ["merge", "geocode", "npi", "trials", "pubmed", "reddit", "finalize"]

if __name__ == "__main__":
    todo = sys.argv[1:] or STAGES
    for s in todo:
        print(f"== {s}", flush=True)
        globals()[f"stage_{s}"]()
