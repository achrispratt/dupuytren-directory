"use client";

import { useRef, useState } from "react";
import { TREATMENTS, type Site } from "@/lib/treatments";

export interface FormState {
  place: string;
  lat?: number;
  lng?: number;
  radius: string;
  site: Site | "both";
  tx: string[];
  match: "any" | "all";
  early: boolean;
  strict: boolean;
  corroborated: boolean;
  country: string;
  name: string;
}

// Treatments worth a chip in the main row; the rest sit under "More treatments".
const PRIMARY: Record<Site | "both", string[]> = {
  hand: ["radiotherapy", "steroid_injection", "needle_aponeurotomy", "collagenase", "fasciectomy"],
  foot: ["radiotherapy", "steroid_injection", "hyaluronidase_injection", "cryoablation", "foot_surgery", "orthotics"],
  both: ["radiotherapy", "steroid_injection", "needle_aponeurotomy", "collagenase", "fasciectomy", "foot_surgery"],
};

export default function SearchForm({
  initial,
  countries,
}: {
  initial: FormState;
  countries: { code: string; name: string; n: number }[];
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [site, setSite] = useState<FormState["site"]>(initial.site);
  const [place, setPlace] = useState(initial.place);
  const [coords, setCoords] = useState<{ lat?: number; lng?: number }>({ lat: initial.lat, lng: initial.lng });
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  const forSite = TREATMENTS.filter((t) => site === "both" || t.sites.includes(site));
  const primary = forSite.filter((t) => PRIMARY[site].includes(t.code));
  const more = forSite.filter((t) => !PRIMARY[site].includes(t.code));
  const moreChecked = more.some((t) => initial.tx.includes(t.code));

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeoError("Your browser doesn't share location. Type a city or postcode instead.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: +pos.coords.latitude.toFixed(4), lng: +pos.coords.longitude.toFixed(4) });
        setPlace("My location");
        setLocating(false);
        setTimeout(() => formRef.current?.requestSubmit(), 0);
      },
      () => {
        setLocating(false);
        setGeoError("Couldn't get your location. Type a city or postcode instead.");
      },
      { timeout: 10000 },
    );
  }

  const chip = (t: (typeof TREATMENTS)[number]) => (
    <label className="chip" key={t.code} title={t.blurb}>
      <input type="checkbox" name="tx" value={t.code} defaultChecked={initial.tx.includes(t.code)} />
      {t.label}
    </label>
  );

  return (
    <form ref={formRef} className="panel search" action="/" method="get" role="search">
      <div className="search-row">
        <label className="field grow">
          Near
          <div className="place-input">
            <input
              type="search"
              name="place"
              placeholder="City, ZIP or postcode (e.g. Denver, 10016, SW19)"
              value={place}
              onChange={(e) => {
                setPlace(e.target.value);
                setCoords({});
              }}
              autoComplete="off"
            />
            <button type="button" className="btn secondary" onClick={useMyLocation} disabled={locating}>
              {locating ? "Locating…" : "📍 Use mine"}
            </button>
          </div>
          {coords.lat != null && <input type="hidden" name="lat" value={coords.lat} />}
          {coords.lng != null && <input type="hidden" name="lng" value={coords.lng} />}
        </label>
        <label className="field">
          Within
          <select name="radius" defaultValue={initial.radius}>
            <option value="50">50 km (30 mi)</option>
            <option value="100">100 km (60 mi)</option>
            <option value="250">250 km (155 mi)</option>
            <option value="500">500 km (310 mi)</option>
            <option value="1000">1,000 km (620 mi)</option>
            <option value="any">Anywhere (sort by distance)</option>
          </select>
        </label>
        <label className="field">
          Country
          <select name="country" defaultValue={initial.country}>
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name} ({c.n})
              </option>
            ))}
          </select>
        </label>
        <button className="btn" type="submit">
          Search
        </button>
      </div>
      {geoError && <p className="notice">{geoError}</p>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <span className="muted" style={{ fontSize: "0.9rem", fontWeight: 600 }}>
          Treating my
        </span>
        <div className="segmented" role="radiogroup" aria-label="Affected area">
          {(["hand", "foot", "both"] as const).map((s) => (
            <label key={s}>
              <input type="radio" name="site" value={s} checked={site === s} onChange={() => setSite(s)} />
              {s === "hand" ? "Hands (Dupuytren's)" : s === "foot" ? "Feet (Ledderhose)" : "Both"}
            </label>
          ))}
        </div>
      </div>

      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="muted" style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 8 }}>
          Who offers… <span style={{ fontWeight: 400 }}>(pick any)</span>
        </legend>
        <div className="chips">{primary.map(chip)}</div>
        {more.length > 0 && (
          <details className="more" open={moreChecked} style={{ marginTop: 8 }}>
            <summary>More treatments</summary>
            <div className="chips" style={{ marginTop: 8 }}>
              {more.map(chip)}
            </div>
          </details>
        )}
      </fieldset>

      <div className="toggles">
        <label>
          <input type="checkbox" name="early" value="1" defaultChecked={initial.early} />
          Treats early-stage disease (before contracture)
        </label>
        <label>
          <input type="checkbox" name="strict" value="1" defaultChecked={initial.strict} />
          Only treatments confirmed by a list or registry
        </label>
        <label>
          <input type="checkbox" name="corroborated" value="1" defaultChecked={initial.corroborated} />
          Only corroborated listings
        </label>
        <label>
          <input type="checkbox" name="match" value="all" defaultChecked={initial.match === "all"} />
          Must offer all selected treatments
        </label>
      </div>
      <details className="more" open={!!initial.name}>
        <summary>Search by doctor or clinic name</summary>
        <input
          type="text"
          name="name"
          defaultValue={initial.name}
          placeholder="e.g. Seegenschmiedt, Pess, Mayo"
          style={{ marginTop: 8, maxWidth: 420 }}
        />
      </details>
    </form>
  );
}
