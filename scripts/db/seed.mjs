// Loads data/build/directory.json into the database in one transaction.
// Listings, treatments, sources and trials are replaced wholesale; submissions are left alone.
import fs from "node:fs";
import path from "node:path";
import { connect } from "./client.mjs";

const file = path.resolve(import.meta.dirname, "../../data/build/directory.json");
const doc = JSON.parse(fs.readFileSync(file, "utf8"));
const db = await connect();

const searchText = (l) =>
  [
    l.name,
    ...l.colleagues,
    l.specialty_label,
    ...l.locations.flatMap((x) => [x.practice, x.city, x.region, x.postal]),
  ]
    .filter(Boolean)
    .join(" ")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

async function insertMany(table, cols, rows, chunk = 300) {
  for (let i = 0; i < rows.length; i += chunk) {
    const part = rows.slice(i, i + chunk);
    const params = [];
    const values = part.map((r) => `(${r.map((v) => (params.push(v), `$${params.length}`)).join(",")})`);
    await db.query(`insert into ${table} (${cols.join(",")}) values ${values.join(",")}`, params);
  }
}

try {
  await db.query("begin");
  await db.query("delete from provider_treatments; delete from provider_sources; delete from locations;");
  await db.query("delete from providers; delete from treatments; delete from sources; delete from trials;");

  await insertMany("sources", ["id", "label", "url", "kind", "page_modified"],
    doc.sources.map((s) => [s.id, s.label, s.url, s.kind, s.page_modified]));
  await insertMany("treatments", ["code", "label"], doc.treatments.map((t) => [t.code, t.label]));

  const L = doc.listings;
  await insertMany("providers",
    ["id", "kind", "name", "honorific", "credential", "specialty", "specialty_label", "colleagues", "website", "websites",
     "emails", "conditions", "countries", "flags", "early_stage", "verification_level", "verification", "npi",
     "publications", "reddit", "trials", "notes", "source_refs", "mention_count", "search_text"],
    L.map((l) => [l.id, l.kind, l.name, l.honorific, l.credential, l.specialty, l.specialty_label, l.colleagues,
      l.website, l.websites, l.emails, l.conditions, l.countries, l.flags, l.early_stage, l.verification.level,
      JSON.stringify(l.verification), l.npi && JSON.stringify(l.npi), l.publications && JSON.stringify(l.publications),
      l.reddit && JSON.stringify(l.reddit), JSON.stringify(l.trials), JSON.stringify(l.notes), JSON.stringify(l.sources),
      l.reddit?.count ?? 0, searchText(l)]), 150);

  await insertMany("locations",
    ["provider_id", "position", "practice", "street", "city", "region", "postal", "country", "phone", "lat", "lng",
     "geo_precision", "from_npi"],
    L.flatMap((l) => l.locations.map((x, i) => [l.id, i, x.practice, x.street, x.city, x.region, x.postal, x.country,
      x.phone, x.lat, x.lng, x.geo_precision, !!x.from_npi])));

  await insertMany("provider_treatments", ["provider_id", "code", "site", "best", "evidence"],
    L.flatMap((l) => l.treatments.map((t) => [l.id, t.code, t.site, t.best, JSON.stringify(t.evidence)])));

  const known = new Set(doc.sources.map((s) => s.id));
  await insertMany("provider_sources", ["provider_id", "source_id"],
    L.flatMap((l) => [...new Set(l.sources.map((s) => s.id))].filter((s) => known.has(s)).map((s) => [l.id, s])));

  await insertMany("trials", ["nct_id", "status", "site", "data"],
    doc.trials.map((t) => [t.nct_id, t.status, t.condition_site, JSON.stringify(t)]), 50);

  await db.query("commit");
  console.log(`seeded ${L.length} providers, ${doc.trials.length} trials (data built ${doc.generated_at})`);
} catch (e) {
  await db.query("rollback").catch(() => {});
  throw e;
} finally {
  await db.end();
}
