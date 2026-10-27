import Link from "next/link";
import SearchForm, { type FormState } from "@/components/SearchForm";
import ProviderCard from "@/components/ProviderCard";
import ResultsMap from "@/components/MapClient";
import { countries as listCountries, search, stats, PAGE_SIZE, type SearchParams } from "@/lib/search";
import { geocodePlace } from "@/lib/geocode";
import { countryName } from "@/lib/format";
import { TREATMENT_BY_CODE } from "@/lib/treatments";

export const dynamic = "force-dynamic";

type Raw = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const many = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);

function parse(sp: Raw): FormState & { page: number } {
  const site = one(sp.site);
  const lat = parseFloat(one(sp.lat));
  const lng = parseFloat(one(sp.lng));
  return {
    place: one(sp.place).slice(0, 120),
    lat: Number.isFinite(lat) ? lat : undefined,
    lng: Number.isFinite(lng) ? lng : undefined,
    radius: one(sp.radius) || "250",
    site: site === "hand" || site === "foot" ? site : "both",
    tx: many(sp.tx).filter((t) => TREATMENT_BY_CODE[t]),
    match: one(sp.match) === "all" ? "all" : "any",
    early: one(sp.early) === "1",
    strict: one(sp.strict) === "1",
    corroborated: one(sp.corroborated) === "1",
    country: /^[A-Z]{2}$/.test(one(sp.country)) ? one(sp.country) : "",
    name: one(sp.name).slice(0, 80),
    page: Math.max(1, parseInt(one(sp.page)) || 1),
  };
}

function pageHref(sp: Raw, page: number) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) for (const x of many(v)) if (k !== "page") q.append(k, x);
  q.set("page", String(page));
  return `/?${q.toString()}`;
}

export default async function Home({ searchParams }: { searchParams: Promise<Raw> }) {
  const sp = await searchParams;
  const f = parse(sp);
  const searched = Object.keys(sp).length > 0;

  let center: { lat: number; lng: number } | null = null;
  let placeLabel = f.place;
  let placeError = false;
  if (f.lat != null && f.lng != null) center = { lat: f.lat, lng: f.lng };
  else if (f.place) {
    const hit = await geocodePlace(f.place);
    if (hit) {
      center = { lat: hit.lat, lng: hit.lng };
      placeLabel = hit.label;
    } else placeError = true;
  }

  const params: SearchParams = {
    lat: center?.lat,
    lng: center?.lng,
    radiusKm: center && f.radius !== "any" ? Number(f.radius) || 250 : null,
    site: f.site,
    tx: f.tx,
    match: f.match,
    early: f.early,
    strict: f.strict,
    corroborated: f.corroborated,
    country: f.country || undefined,
    name: f.name || undefined,
    page: f.page,
  };
  const [{ results, total, points }, s, cs] = await Promise.all([search(params), stats(), listCountries()]);
  const pages = Math.ceil(total / PAGE_SIZE);
  const txNames = f.tx.map((t) => TREATMENT_BY_CODE[t].label.toLowerCase());

  return (
    <>
      <section className="hero">
        <h1>Find a doctor who treats Dupuytren&apos;s or Ledderhose</h1>
        <p>
          Search by the treatments doctors actually offer, from early-stage radiation and steroid injections to needle
          release, Xiaflex and surgery, for hands and feet. Every listing shows where the information came from.
        </p>
        {s && (
          <div className="stats">
            <span>
              <b>{s.providers.toLocaleString()}</b> doctors &amp; clinics
            </span>
            <span>
              <b>{s.countries}</b> countries
            </span>
            <span>
              <b>{s.rt}</b> offering radiation therapy
            </span>
            <span>
              <b>{s.ledderhose}</b> treating Ledderhose
            </span>
            <span>
              <b>{s.early}</b> treating early-stage disease
            </span>
          </div>
        )}
      </section>

      <SearchForm
        initial={{ ...f, place: f.place }}
        countries={cs.map((c) => ({ code: c.country, name: countryName(c.country), n: c.n }))}
      />

      {placeError && (
        <p className="notice">
          We couldn&apos;t find “{f.place}”. Try a city name or a postcode with its country, e.g. “Leeds UK”.
        </p>
      )}

      <div className="results-layout">
        <section aria-live="polite">
          <div className="results-head">
            <h2 style={{ margin: 0 }}>
              {total.toLocaleString()} {total === 1 ? "result" : "results"}
              {txNames.length > 0 && <span className="muted" style={{ fontWeight: 400 }}> offering {txNames.join(f.match === "all" ? " and " : " or ")}</span>}
              {center && <span className="muted" style={{ fontWeight: 400 }}> near {placeLabel}</span>}
            </h2>
            {!searched && <span className="muted">Showing corroborated listings first. Add a location to sort by distance.</span>}
          </div>
          {f.site === "foot" && (
            <p className="notice info">
              Few doctors list Ledderhose treatment specifically. Radiation clinics that treat Dupuytren&apos;s usually
              treat Ledderhose too, so they appear here marked <b>Likely</b>. Ask before booking.
            </p>
          )}
          {results.length === 0 ? (
            <div className="panel empty">
              <p>No listings match all of that.</p>
              <p>
                Try a bigger radius, “Anywhere”, or fewer treatments. Many patients travel for radiation therapy. Know a
                doctor we&apos;re missing? <Link href="/suggest">Suggest them</Link>.
              </p>
            </div>
          ) : (
            results.map((p) => <ProviderCard key={p.id} p={p} site={f.site} tx={f.tx} />)
          )}
          {pages > 1 && (
            <nav className="pager" aria-label="Pages">
              {f.page > 1 && (
                <Link className="btn secondary" href={pageHref(sp, f.page - 1)}>
                  ← Previous
                </Link>
              )}
              <span className="muted">
                Page {f.page} of {pages}
              </span>
              {f.page < pages && (
                <Link className="btn secondary" href={pageHref(sp, f.page + 1)}>
                  Next →
                </Link>
              )}
            </nav>
          )}
        </section>
        <aside className="map-col" aria-label="Map of results">
          <ResultsMap points={points} center={center} highlight={results.map((r) => r.id)} />
          <p className="muted" style={{ fontSize: "0.82rem", marginTop: 6 }}>
            {points.length.toLocaleString()} matching listings on the map. Larger dots are on this page. Some listings
            are placed at city level only.
          </p>
        </aside>
      </div>
    </>
  );
}
