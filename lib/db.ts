import "server-only";
import { neon } from "@neondatabase/serverless";
import pg from "pg";

type Row = Record<string, unknown>;
type Query = <T = Row>(text: string, params?: unknown[]) => Promise<T[]>;

let query: Query | null = null;

/** Neon's HTTP driver in production (fast cold starts on Vercel); node-postgres for local Postgres. */
export function db(): Query {
  if (query) return query;
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set. Copy .env.example to .env.local.");
  if (/neon\.tech/.test(url)) {
    const sql = neon(url);
    query = async <T,>(text: string, params: unknown[] = []) =>
      (await sql.query(text, params)) as unknown as T[];
  } else {
    const pool = new pg.Pool({ connectionString: url, max: 5 });
    query = async <T,>(text: string, params: unknown[] = []) => (await pool.query(text, params)).rows as T[];
  }
  return query;
}
