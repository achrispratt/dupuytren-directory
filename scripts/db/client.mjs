// Plain node-postgres client for scripts. Works against Neon (sslmode=require in the URL) and local Postgres.
import pg from "pg";

export async function connect() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  const ssl = /sslmode=require|neon\.tech/.test(url) ? { rejectUnauthorized: false } : undefined;
  const client = new pg.Client({ connectionString: url, ssl });
  await client.connect();
  return client;
}
