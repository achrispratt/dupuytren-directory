import "server-only";
import { db } from "./db";

export interface Place {
  lat: number;
  lng: number;
  label: string;
  country?: string;
}

/** Resolve what the user typed ("Denver", "SW19 5NB", "80202") to a point. Cached in Postgres; OSM Nominatim upstream. */
export async function geocodePlace(q: string): Promise<Place | null> {
  const query = q.trim().toLowerCase().replace(/\s+/g, " ");
  if (!query) return null;
  const cached = await db()<{ result: Place | null }>("select result from geocode_cache where query = $1", [query]);
  if (cached.length) return cached[0].result;
  let place: Place | null = null;
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&addressdetails=1&q=${encodeURIComponent(q)}`;
    const res = await fetch(url, {
      headers: { "User-Agent": "dupuytren-directory (github.com/achrispratt/dupuytren-directory)" },
      signal: AbortSignal.timeout(6000),
    });
    if (res.ok) {
      const [hit] = (await res.json()) as { lat: string; lon: string; display_name: string; address?: { country_code?: string } }[];
      if (hit) {
        place = {
          lat: Number(hit.lat),
          lng: Number(hit.lon),
          label: hit.display_name.split(",").slice(0, 3).join(",").trim(),
          country: hit.address?.country_code?.toUpperCase(),
        };
      }
    }
  } catch {
    return null; // don't cache failures
  }
  await db()("insert into geocode_cache (query, result) values ($1, $2) on conflict (query) do nothing", [
    query,
    place ? JSON.stringify(place) : null,
  ]);
  return place;
}
