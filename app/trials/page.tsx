import type { Metadata } from "next";
import { db } from "@/lib/db";

export const metadata: Metadata = {
  title: "Clinical trials",
  description: "Dupuytren's and Ledderhose clinical trials from ClinicalTrials.gov, open studies first.",
};
export const dynamic = "force-dynamic";

interface Trial {
  nct_id: string;
  title: string;
  status: string;
  start: string | null;
  completion: string | null;
  phases: string[];
  conditions: string[];
  interventions: string[];
  sponsor: string | null;
  summary: string | null;
  enrollment: number | null;
  locations: { facility: string | null; city: string | null; country: string | null; status: string | null }[];
  url: string;
}

const OPEN = ["RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"];
const LABEL: Record<string, string> = {
  RECRUITING: "Recruiting",
  NOT_YET_RECRUITING: "Not yet recruiting",
  ENROLLING_BY_INVITATION: "By invitation",
  ACTIVE_NOT_RECRUITING: "Active, not recruiting",
  COMPLETED: "Completed",
  TERMINATED: "Terminated",
  WITHDRAWN: "Withdrawn",
  UNKNOWN: "Status unknown",
};

function firstSentences(s: string | null, n = 2) {
  if (!s) return "";
  const parts = s.replace(/\s+/g, " ").match(/[^.!?]+[.!?]+/g) ?? [s];
  return parts.slice(0, n).join(" ").trim();
}

export default async function TrialsPage() {
  const rows = await db()<{ data: Trial; site: string }>(
    "select data, site from trials order by (status = any($1)) desc, (status = 'ACTIVE_NOT_RECRUITING') desc, data->>'start' desc nulls last",
    [OPEN],
  );
  const open = rows.filter((r) => OPEN.includes(r.data.status));
  const rest = rows.filter((r) => !OPEN.includes(r.data.status));
  const card = ({ data: t, site }: { data: Trial; site: string }) => {
    const countries = [...new Set(t.locations.map((l) => l.country).filter(Boolean))];
    return (
      <article key={t.nct_id} className="panel trial">
        <div className="meta-row" style={{ marginBottom: 6 }}>
          <span className={`status ${t.status}`}>{LABEL[t.status] ?? t.status}</span>
          <span className={`pill ${site === "foot" ? "foot" : "hand"}`}>{site === "foot" ? "Ledderhose" : "Dupuytren's"}</span>
          {t.phases?.filter((p) => p !== "NA").map((p) => (
            <span key={p} className="badge listed">
              {p.replace("PHASE", "Phase ")}
            </span>
          ))}
        </div>
        <h3 style={{ margin: "0 0 4px" }}>
          <a href={t.url} target="_blank" rel="noopener noreferrer">
            {t.title}
          </a>
        </h3>
        <p className="muted" style={{ fontSize: "0.9rem", margin: "0 0 6px" }}>
          {[t.sponsor, t.interventions.slice(0, 3).join(", "), t.start && `started ${t.start}`].filter(Boolean).join(" · ")}
        </p>
        <p style={{ fontSize: "0.93rem", margin: "0 0 6px" }}>{firstSentences(t.summary)}</p>
        {t.locations.length > 0 && (
          <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>
            {t.locations.length} site{t.locations.length > 1 ? "s" : ""}: {countries.join(", ")}
            {t.locations.length <= 4 && ` (${t.locations.map((l) => [l.facility, l.city].filter(Boolean).join(", ")).join("; ")})`}
          </p>
        )}
      </article>
    );
  };
  return (
    <div style={{ margin: "24px 0 40px" }}>
      <h1>Clinical trials</h1>
      <p className="muted prose">
        Every Dupuytren&apos;s and Ledderhose study registered on ClinicalTrials.gov, open studies first. Recruiting sites
        also appear in the doctor search. Talk to the study team about eligibility before you travel.
      </p>
      <h2 style={{ marginTop: 20 }}>Open or upcoming ({open.length})</h2>
      {open.map(card)}
      <details style={{ marginTop: 20 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>Closed, completed or unknown ({rest.length})</summary>
        <div style={{ marginTop: 12 }}>{rest.map(card)}</div>
      </details>
    </div>
  );
}
