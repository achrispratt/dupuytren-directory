# Dupuytren's & Ledderhose Directory

A public, patient-facing directory of doctors and clinics that treat **Dupuytren's contracture** (hands) and
**Ledderhose disease** (feet), searchable by the treatments they actually offer: radiation therapy, steroid
injections, needle aponeurotomy, collagenase (Xiaflex), fasciectomy, dermofasciectomy and foot-specific care.

Every listing records **where each fact came from** and **how well it is verified**. Nothing is invented: a doctor
only appears if a patient organisation list, a trial registry or the NPI registry names them.

## Stack

- Next.js (App Router) on **Vercel**
- **Neon** Postgres (`@neondatabase/serverless` HTTP driver in production, `pg` locally)
- Leaflet + OpenStreetMap for maps
- Python 3 (stdlib only) for the data pipeline

## Data pipeline

```
data/raw/        snapshots of the source pages (IDS English + German, BDS list, BDS Google map KML)
data/curated/    hand-transcribed lists, kept faithful to the source pages (format documented at the top of each file)
scripts/ingest/  build pipeline
data/build/      outputs: listings.json (intermediate), directory.json (what gets seeded)
data/cache/      API caches (geocoding, NPI, PubMed, Reddit archive) so rebuilds are cheap
```

`python3 scripts/ingest/build.py` runs these stages (or name stages to run a subset):

| Stage | What it does |
| --- | --- |
| `merge` | Parses curated lists + BDS map, splits group practices into clinicians, de-duplicates across sources |
| `geocode` | US Census geocoder for US addresses, Nominatim (1 req/s) elsewhere |
| `npi` | Matches US clinicians to the CMS NPPES registry (unique match by name, state, relevant taxonomy) |
| `trials` | Pulls every Dupuytren/Ledderhose study from ClinicalTrials.gov; open sites become listings |
| `pubmed` | Counts Dupuytren/Ledderhose papers per doctor, only where the author affiliation matches their location |
| `reddit` | Matches mentions in the r/DupuytrenDisease archive (Arctic Shift) to listed doctors as patient reports |
| `finalize` | Computes treatment evidence and verification level, writes `data/build/directory.json` |

### Evidence and verification

Each treatment on a listing carries evidence, strongest first: `listed` (a patient organisation says so),
`trial_site`, `trial_investigator`, `patient_reported` (Reddit), `inferred` (radiation clinics treating
Ledderhose, per BDS guidance). Search can be restricted to listed evidence only.

Listing status:

- **corroborated**: NPI match, two independent organisations, or a registered trial site
- **listed**: one patient organisation list
- **needs_review**: a source flags retirement or a move, the only source is stale, or a US doctor has no unique NPI match

Reddit never creates a listing. Doctors patients name often but who aren't listed go to
`data/build/reddit_unmatched.json` for manual review.

## Running locally

```bash
npm install
cp .env.example .env.local          # set DATABASE_URL (any Postgres 14+ with pg_trgm)
npm run db:setup                    # migrate + seed from data/build/directory.json
npm run dev
```

Tests: `npm test` (pipeline unit tests), `npm run lint` (type check).

## Deploying (Vercel + Neon)

1. Import the repo into Vercel.
2. In the Vercel project, **Storage → Create → Neon**. This sets `DATABASE_URL`.
3. Set `ADMIN_TOKEN` (any long random string) to enable `/admin` moderation of submissions.
4. Load the data once from your machine: `DATABASE_URL=<neon url> npm run db:setup`.

Re-seeding replaces directory data but keeps user submissions.

## Refreshing the data

Re-snapshot the source pages into `data/raw/`, update `data/curated/` where lists changed, then
`npm run data:build && npm run db:seed`. Caches make reruns fast; delete a cache file to force a refetch.

Not medical advice. Listing is not endorsement.
