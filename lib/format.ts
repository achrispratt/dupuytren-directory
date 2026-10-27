import countries from "./countries.json";

const NAMES = countries as Record<string, string>;
const MILES = new Set(["US", "GB", "LR", "MM"]);

export function countryName(cc: string) {
  return NAMES[cc] ?? cc;
}

export function formatDistance(km: number, country?: string | null) {
  if (country && MILES.has(country)) {
    const mi = km * 0.621371;
    return `${mi < 10 ? mi.toFixed(1) : Math.round(mi).toLocaleString()} mi`;
  }
  return `${km < 10 ? km.toFixed(1) : Math.round(km).toLocaleString()} km`;
}

export function placeLine(l: { city: string | null; region: string | null; postal?: string | null }) {
  return [l.city, l.region].filter(Boolean).join(", ") || "—";
}

export function addressLines(l: {
  practice: string | null;
  street: string | null;
  city: string | null;
  region: string | null;
  postal: string | null;
  country: string;
}) {
  const cityLine =
    l.country === "US" || l.country === "CA" || l.country === "AU"
      ? [l.city, [l.region, l.postal].filter(Boolean).join(" ")].filter(Boolean).join(", ")
      : [l.postal, l.city].filter(Boolean).join(" ") + (l.region && l.country === "GB" ? `, ${l.region}` : "");
  return [l.street, cityLine, countryName(l.country)].filter(Boolean);
}

export function telHref(phone: string) {
  return "tel:" + phone.replace(/[^\d+]/g, "");
}

export function host(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
