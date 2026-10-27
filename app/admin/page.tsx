import type { Metadata } from "next";
import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";

export const metadata: Metadata = { title: "Moderation", robots: { index: false } };
export const dynamic = "force-dynamic";

interface Submission {
  id: string;
  kind: string;
  provider_id: string | null;
  payload: Record<string, unknown>;
  contact: string | null;
  status: string;
  created_at: string;
}

function authorized(token?: string) {
  return !!process.env.ADMIN_TOKEN && token === process.env.ADMIN_TOKEN;
}

async function setStatus(form: FormData) {
  "use server";
  if (!authorized(String(form.get("token")))) return;
  await db()("update submissions set status = $1 where id = $2", [String(form.get("status")), String(form.get("id"))]);
  revalidatePath("/admin");
}

export default async function Admin({ searchParams }: { searchParams: Promise<{ token?: string; all?: string }> }) {
  const { token, all } = await searchParams;
  if (!authorized(token)) {
    return <p className="panel empty" style={{ margin: "40px 0" }}>Set ADMIN_TOKEN and open /admin?token=…</p>;
  }
  const rows = await db()<Submission & Record<string, unknown>>(
    `select * from submissions ${all ? "" : "where status = 'pending'"} order by created_at desc limit 200`,
  );
  return (
    <div style={{ margin: "24px 0 40px" }}>
      <h1>Submissions ({rows.length})</h1>
      <p className="muted">
        Accepting marks a submission as reviewed. Apply the change in <code>data/curated/</code> and rebuild so it carries
        its source.
      </p>
      {rows.map((s) => (
        <article key={s.id} className="panel card">
          <div className="meta-row">
            <span className="badge listed">{s.kind}</span>
            <span className="badge listed">{s.status}</span>
            <small className="muted">{new Date(s.created_at).toISOString().slice(0, 16)}</small>
            {s.provider_id && <a href={`/p/${s.provider_id}`}>{s.provider_id}</a>}
            {s.contact && <small>{s.contact}</small>}
          </div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", margin: 0 }}>{JSON.stringify(s.payload, null, 2)}</pre>
          <form action={setStatus} style={{ display: "flex", gap: 8 }}>
            <input type="hidden" name="id" value={s.id} />
            <input type="hidden" name="token" value={token} />
            <button className="btn" name="status" value="accepted">Accept</button>
            <button className="btn secondary" name="status" value="rejected">Reject</button>
          </form>
        </article>
      ))}
    </div>
  );
}
