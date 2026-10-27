// Applies db/migrations/*.sql in order, once each.
import fs from "node:fs";
import path from "node:path";
import { connect } from "./client.mjs";

const dir = path.resolve(import.meta.dirname, "../../db/migrations");
const db = await connect();
try {
  await db.query("create table if not exists schema_migrations (name text primary key, applied_at timestamptz not null default now())");
  const done = new Set((await db.query("select name from schema_migrations")).rows.map((r) => r.name));
  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith(".sql")).sort()) {
    if (done.has(file)) continue;
    await db.query("begin");
    await db.query(fs.readFileSync(path.join(dir, file), "utf8"));
    await db.query("insert into schema_migrations (name) values ($1)", [file]);
    await db.query("commit");
    console.log(`applied ${file}`);
  }
} catch (e) {
  await db.query("rollback").catch(() => {});
  throw e;
} finally {
  await db.end();
}
