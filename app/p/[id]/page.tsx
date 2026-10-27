import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import ResultsMap from "@/components/MapClient";
import { VerificationBadge } from "@/components/ProviderCard";
import { getProvider } from "@/lib/search";
import { addressLines, host, telHref } from "@/lib/format";
import { EVIDENCE, TREATMENT_BY_CODE, type Evidence } from "@/lib/treatments";

export const dynamic = "force-dynamic";

const FLAG_LABELS: Record<string, string> = {
  nhs: "NHS",
  private: "Private patients",
  video_consult: "Video consultations",
  rt_referral: "Open to referring for radiation therapy",
  treats_children: "Treats children",
  revision_surgery: "Revision / recurrent cases",
  walant: "Wide-awake (local anaesthetic) surgery",
  trained_paris: "Trained in needle aponeurotomy in Paris",
  musicians: "Musicians clinic",
  referral_required: "Referral required",
  ultrasound_guided: "Ultrasound-guided",
  treats_ledderhose: "Treats Ledderhose",
  early_stage: "Treats early-stage disease",
  clinical_trial: "Recruiting a clinical trial",
};

interface Provider {
  id: string;
  kind: string;
  name: string;
  honorific: string | null;
  credential: string | null;
  specialty_label: string | null;
  colleagues: string[];
  websites: string[];
  emails: string[];
  flags: string[];
  verification_level: "corroborated" | "listed" | "needs_review";
  verification: { reasons: string[]; warnings: string[]; checked: string };
  npi: { npi: string; taxonomy: string; credential: string; updated: string } | null;
  publications: { count: number; topics: Record<string, number>; recent: { pmid: string; title: string; year: string; journal: string }[] } | null;
  reddit: { count: number; mentions: { url: string; date: string; snippet: string; treatments: string[] }[] } | null;
  trials: { nct_id: string; title: string; status: string }[];
  notes: { source: string; text: string }[];
}

async function load(id: string) {
  const data = await getProvider(id);
  if (!data) notFound();
  return { ...data, provider: data.provider as unknown as Provider };
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const data = await getProvider(id);
  if (!data) return { title: "Not found" };
  const p = data.provider as unknown as Provider;
  const where = data.locations[0]?.city;
  return {
    title: `${[p.honorific, p.name].filter(Boolean).join(" ")}${where ? `, ${where}` : ""}`,
    description: `Dupuytren's / Ledderhose treatments offered by ${p.name}, with sources.`,
  };
}

export default async function ProviderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { provider: p, locations, treatments, sources } = await load(id);
  const who = p.kind === "clinician" ? [p.honorific, p.name].filter(Boolean).join(" ") : p.name;
  const sourceById = Object.fromEntries(sources.map((s) => [s.id, s]));
  const points = locations
    .filter((l) => l.lat != null && l.lng != null)
    .map((l, i) => ({ id: `${p.id}-${i}`, name: l.practice || who, lat: l.lat!, lng: l.lng!, level: p.verification_level }));
  const tx = [...treatments].sort(
    (a, b) => a.site.localeCompare(b.site) || EVIDENCE[a.best].rank - EVIDENCE[b.best].rank,
  );

  return (
    <div className="detail">
      <div>
        <p style={{ marginTop: 0 }}>
          <Link href="/">← Back to search</Link>
        </p>
        <section className="panel section">
          <h1 style={{ marginBottom: 4 }}>
            {who}
            {p.credential && <span className="muted" style={{ fontWeight: 400, fontSize: "0.7em" }}>, {p.credential}</span>}
          </h1>
          <p className="muted">
            {[p.specialty_label, p.kind === "practice" ? "Clinic / team" : null].filter(Boolean).join(" · ")}
          </p>
          {p.colleagues.length > 0 && (
            <p style={{ fontSize: "0.93rem" }}>
              <span className="muted">{p.kind === "clinician" ? "Listed alongside: " : "Clinicians: "}</span>
              {p.colleagues.join(", ")}
            </p>
          )}
          <div className="meta-row" style={{ marginBottom: 10 }}>
            <VerificationBadge level={p.verification_level} />
            {p.flags.filter((f) => FLAG_LABELS[f]).map((f) => (
              <span key={f} className={`badge ${f === "early_stage" ? "early" : "listed"}`}>
                {FLAG_LABELS[f]}
              </span>
            ))}
          </div>
          {p.verification.reasons.length > 0 && (
            <ul style={{ margin: "0 0 8px", paddingLeft: 18, fontSize: "0.92rem" }}>
              {p.verification.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {p.verification.warnings.map((w) => (
            <p key={w} className="notice">
              {w}
            </p>
          ))}
        </section>

        <section className="panel section">
          <h2>Treatments</h2>
          <table className="tx">
            <thead>
              <tr>
                <th>Treatment</th>
                <th>For</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {tx.map((t) => (
                <tr key={`${t.code}:${t.site}`}>
                  <td>
                    <b>{TREATMENT_BY_CODE[t.code]?.label ?? t.code}</b>
                  </td>
                  <td>{t.site === "hand" ? "Hands" : "Feet"}</td>
                  <td>
                    <span className={`pill ${t.site} ev-${t.best}`} title={EVIDENCE[t.best].long}>
                      {EVIDENCE[t.best].label}
                    </span>{" "}
                    <EvidenceLinks evidence={t.evidence} sources={sourceById} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: 10 }}>
            Practices change what they offer. Call ahead to confirm, and ask how often they do it.
          </p>
        </section>

        {p.reddit && p.reddit.count > 0 && (
          <section className="panel section">
            <h2>What patients have said ({p.reddit.count})</h2>
            <p className="muted" style={{ fontSize: "0.88rem" }}>
              Excerpts from r/DupuytrenDisease that mention this name. They are individual experiences, and a few may
              refer to a different doctor with the same surname.
            </p>
            {p.reddit.mentions.map((m) => (
              <blockquote key={m.url} className="quote">
                {m.snippet}
                <small>
                  <a href={m.url} target="_blank" rel="noopener noreferrer nofollow">
                    Read on Reddit
                  </a>{" "}
                  · {m.date}
                  {m.treatments.length > 0 &&
                    ` · mentions ${m.treatments.map((c) => TREATMENT_BY_CODE[c]?.label.toLowerCase() ?? c).join(", ")}`}
                </small>
              </blockquote>
            ))}
          </section>
        )}

        {(p.trials.length > 0 || (p.publications && p.publications.count > 0)) && (
          <section className="panel section">
            <h2>Research</h2>
            {p.trials.length > 0 && (
              <>
                <h3>Clinical trials</h3>
                <ul className="plain">
                  {p.trials.map((t) => (
                    <li key={t.nct_id}>
                      <a href={`https://clinicaltrials.gov/study/${t.nct_id}`} target="_blank" rel="noopener noreferrer">
                        {t.title}
                      </a>{" "}
                      <span className={`status ${t.status}`}>{t.status.replaceAll("_", " ").toLowerCase()}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {p.publications && p.publications.count > 0 && (
              <>
                <h3 style={{ marginTop: 12 }}>
                  {p.publications.count} paper{p.publications.count > 1 ? "s" : ""} on Dupuytren&apos;s or Ledderhose
                </h3>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  PubMed papers where an author with this name lists an affiliation in the same city or country.
                </p>
                <ul className="plain">
                  {p.publications.recent.map((a) => (
                    <li key={a.pmid}>
                      <a href={`https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/`} target="_blank" rel="noopener noreferrer">
                        {a.title}
                      </a>{" "}
                      <small className="muted">
                        {a.journal} {a.year}
                      </small>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}

        {p.notes.length > 0 && (
          <section className="panel section">
            <h2>Notes from sources</h2>
            <ul className="plain">
              {p.notes.map((n, i) => (
                <li key={i}>
                  {n.text} <small className="muted">({sourceById[n.source]?.label ?? n.source})</small>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <aside>
        <section className="panel section">
          <h2>
            {locations.length > 1 ? `${locations.length} locations` : "Location"}
          </h2>
          {points.length > 0 && <ResultsMap points={points} />}
          {locations.map((l, i) => (
            <div className="loc" key={i}>
              {l.practice && <b>{l.practice}</b>}
              {addressLines(l).map((line) => (
                <div key={line}>{line}</div>
              ))}
              {l.phone && (
                <div>
                  <a href={telHref(l.phone)}>{l.phone}</a>
                </div>
              )}
              {l.from_npi && <small className="muted">From the NPI registry (current address on file).</small>}
              {l.geo_precision && l.geo_precision !== "street" && (
                <small className="muted" style={{ display: "block" }}>
                  Map pin is approximate ({l.geo_precision} level).
                </small>
              )}
            </div>
          ))}
          {(p.websites.length > 0 || p.emails.length > 0) && (
            <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
              {p.websites.map((w) => (
                <a key={w} href={w} target="_blank" rel="noopener noreferrer nofollow">
                  {host(w)} ↗
                </a>
              ))}
              {p.emails.map((e) => (
                <a key={e} href={`mailto:${e}`}>
                  {e}
                </a>
              ))}
            </div>
          )}
        </section>

        <section className="panel section">
          <h2>Sources</h2>
          <ul className="plain">
            {sources.map((s) => (
              <li key={s.id}>
                <a href={s.url} target="_blank" rel="noopener noreferrer">
                  {s.label}
                </a>
                {s.page_modified && <small className="muted"> · page updated {String(s.page_modified).slice(0, 10)}</small>}
              </li>
            ))}
            {p.npi && (
              <li>
                <a href={`https://npiregistry.cms.hhs.gov/provider-view/${p.npi.npi}`} target="_blank" rel="noopener noreferrer">
                  NPI Registry: {p.npi.npi}
                </a>
                <small className="muted"> · {p.npi.taxonomy}</small>
              </li>
            )}
          </ul>
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: 8 }}>
            Checked {p.verification.checked}.
          </p>
        </section>

        <section className="panel section">
          <h2>Know this doctor?</h2>
          <p style={{ fontSize: "0.93rem" }}>Help other patients: tell us what they offered you, or fix something wrong here.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn" href={`/suggest?provider=${p.id}&kind=experience`}>
              Share your experience
            </Link>
            <Link className="btn secondary" href={`/suggest?provider=${p.id}&kind=correction`}>
              Report a correction
            </Link>
          </div>
        </section>
      </aside>
    </div>
  );
}

function EvidenceLinks({
  evidence,
  sources,
}: {
  evidence: { source: string; evidence: Evidence; ref?: string; note?: string }[];
  sources: Record<string, { label: string; url: string }>;
}) {
  const seen = new Set<string>();
  const items = evidence.filter((e) => {
    const k = e.source + (e.evidence === "patient_reported" ? "" : e.ref ?? "");
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return (
    <small className="muted">
      {items.map((e, i) => {
        const s = sources[e.source];
        const label =
          e.source === "reddit"
            ? `patient reports (${evidence.filter((x) => x.source === "reddit").length})`
            : e.source === "ctgov"
              ? e.ref
              : (s?.label.split(":")[0] ?? e.source);
        const href = e.source === "ctgov" && e.ref ? `https://clinicaltrials.gov/study/${e.ref}` : e.source === "reddit" ? e.ref : s?.url;
        return (
          <span key={i}>
            {i > 0 && ", "}
            {href ? (
              <a href={href} target="_blank" rel="noopener noreferrer nofollow">
                {label}
              </a>
            ) : (
              label
            )}
          </span>
        );
      })}
      {evidence[0]?.note && <> · {evidence[0].note}</>}
    </small>
  );
}

