import "server-only";
import { db } from "./db";
import type { Evidence, Site } from "./treatments";

export interface SearchParams {
  place?: string; // free text the user typed ("Denver", "SW19", "80202")
  lat?: number;
  lng?: number;
  radiusKm?: number | null; // null = anywhere
  site?: Site | "both";
  tx: string[];
  match: "any" | "all";
  early: boolean;
  strict: boolean; // only evidence from a list or registry (no patient reports, no inferred)
  corroborated: boolean;
  country?: string;
  name?: string;
  page: number;
}

export interface LocationRow {
  practice: string | null;
  street: string | null;
  city: string | null;
  region: string | null;
  postal: string | null;
  country: string;
  phone: string | null;
  lat: number | null;
  lng: number | null;
  geo_precision: string | null;
  from_npi: boolean;
}

export interface TreatmentRow {
  code: string;
  site: Site;
  best: Evidence;
  evidence: { source: string; evidence: Evidence; ref?: string; note?: string }[];
}

export interface ProviderSummary {
  id: string;
  kind: "clinician" | "practice" | "trial_site";
  name: string;
  honorific: string | null;
  credential: string | null;
  specialty_label: string | null;
  colleagues: string[];
  website: string | null;
  flags: string[];
  conditions: string[];
  early_stage: boolean;
  verification_level: "corroborated" | "listed" | "needs_review";
  mention_count: number;
  distance_km: number | null;
  nearest: LocationRow | null;
  location_count: number;
  treatments: TreatmentRow[];
}

export interface MapPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  level: string;
}

export const PAGE_SIZE = 25;
const STRICT: Evidence[] = ["listed", "trial_site", "trial_investigator"];
const ALL: Evidence[] = ["listed", "trial_site", "trial_investigator", "patient_reported", "inferred"];

function where(p: SearchParams) {
  const params: unknown[] = [];
  const add = (v: unknown) => (params.push(v), `$${params.length}`);
  const clauses: string[] = [];
  const evidence = p.strict ? STRICT : ALL;
  const sites: Site[] = p.site === "hand" ? ["hand"] : p.site === "foot" ? ["foot"] : ["hand", "foot"];

  if (p.tx.length) {
    if (p.match === "all") {
      for (const code of p.tx) {
        clauses.push(`exists (select 1 from provider_treatments t where t.provider_id = p.id and t.code = ${add(code)}
          and t.site = any(${add(sites)}) and t.best = any(${add(evidence)}))`);
      }
    } else {
      clauses.push(`exists (select 1 from provider_treatments t where t.provider_id = p.id and t.code = any(${add(p.tx)})
        and t.site = any(${add(sites)}) and t.best = any(${add(evidence)}))`);
    }
  } else if (p.site && p.site !== "both") {
    clauses.push(`exists (select 1 from provider_treatments t where t.provider_id = p.id and t.site = ${add(p.site)}
      and t.best = any(${add(evidence)}))`);
  }
  if (p.early) clauses.push("p.early_stage");
  if (p.corroborated) clauses.push("p.verification_level = 'corroborated'");
  if (p.country) clauses.push(`${add(p.country)} = any(p.countries)`);
  if (p.name) {
    const q = p.name.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
    clauses.push(`p.search_text like ${add(`%${q}%`)}`);
  }
  return { clauses, params, add };
}

export async function search(p: SearchParams) {
  const { clauses, params, add } = where(p);
  const hasPoint = p.lat != null && p.lng != null;
  const dist = hasPoint
    ? `6371 * 2 * asin(sqrt(power(sin(radians(l.lat - ${add(p.lat)}) / 2), 2) +
         cos(radians(${add(p.lat)})) * cos(radians(l.lat)) * power(sin(radians(l.lng - ${add(p.lng)}) / 2), 2)))`
    : "null::float";
  const near = `
    select distinct on (l.provider_id) ${dist} as d, l.*
    from locations l
    ${hasPoint ? "where l.lat is not null" : ""}
    order by l.provider_id, ${hasPoint ? "d asc nulls last" : "l.position"}`;
  if (hasPoint && p.radiusKm) clauses.push(`n.d <= ${add(p.radiusKm)}`);
  const whereSql = clauses.length ? `where ${clauses.join(" and ")}` : "";
  const order = hasPoint
    ? "n.d asc nulls last, p.verification_level = 'corroborated' desc, p.mention_count desc"
    : "(p.verification_level = 'corroborated') desc, p.mention_count desc, p.name";

  const sql = `
    with near as (${near})
    select p.id, p.kind, p.name, p.honorific, p.credential, p.specialty_label, p.colleagues, p.website, p.flags,
           p.conditions, p.early_stage, p.verification_level, p.mention_count,
           n.d as distance_km,
           to_jsonb(n) - 'provider_id' - 'd' - 'id' - 'position' as nearest,
           (select count(*) from locations x where x.provider_id = p.id)::int as location_count,
           (select coalesce(jsonb_agg(jsonb_build_object('code', t.code, 'site', t.site, 'best', t.best)
                     order by t.site, t.code), '[]') from provider_treatments t where t.provider_id = p.id) as treatments,
           count(*) over ()::int as total
    from providers p
    left join near n on n.provider_id = p.id
    ${whereSql}
    order by ${order}
    limit ${PAGE_SIZE} offset ${add((p.page - 1) * PAGE_SIZE)}`;
  const rows = await db()<ProviderSummary & { total: number }>(sql, params);

  // map: every match (positions only), capped
  const mapSql = `
    with near as (${near})
    select p.id, p.name, p.verification_level as level, n.lat, n.lng
    from providers p join near n on n.provider_id = p.id
    ${whereSql ? whereSql + " and" : "where"} n.lat is not null
    limit 1500`;
  const mapParams = params.slice(0, params.length - 1);
  const points = await db()<MapPoint>(mapSql, mapParams);
  return { results: rows, total: rows[0]?.total ?? 0, points };
}

export async function getProvider(id: string) {
  const [p] = await db()(`select * from providers where id = $1`, [id]);
  if (!p) return null;
  const locations = await db()<LocationRow & Record<string, unknown>>(
    `select * from locations where provider_id = $1 order by position`,
    [id],
  );
  const treatments = await db()<TreatmentRow & Record<string, unknown>>(
    `select code, site, best, evidence from provider_treatments where provider_id = $1`,
    [id],
  );
  const sources = await db()<{ id: string; label: string; url: string; kind: string; page_modified: string | null } & Record<string, unknown>>(
    `select s.* from sources s join provider_sources ps on ps.source_id = s.id where ps.provider_id = $1`,
    [id],
  );
  return { provider: p, locations, treatments, sources };
}

export async function stats() {
  const [r] = await db()<{ providers: number; countries: number; rt: number; ledderhose: number; early: number }>(`
    select (select count(*) from providers)::int as providers,
           (select count(distinct country) from locations)::int as countries,
           (select count(distinct provider_id) from provider_treatments where code = 'radiotherapy' and best <> 'inferred')::int as rt,
           (select count(distinct provider_id) from provider_treatments where site = 'foot' and best <> 'inferred')::int as ledderhose,
           (select count(*) from providers where early_stage)::int as early`);
  return r;
}

export async function countries() {
  return db()<{ country: string; n: number }>(
    `select country, count(distinct provider_id)::int as n from locations group by country order by n desc`,
  );
}
