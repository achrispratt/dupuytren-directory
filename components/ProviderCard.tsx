import Link from "next/link";
import type { ProviderSummary } from "@/lib/search";
import { TREATMENT_BY_CODE, EVIDENCE, type Site } from "@/lib/treatments";
import { countryName, formatDistance, placeLine } from "@/lib/format";

export function VerificationBadge({ level }: { level: ProviderSummary["verification_level"] }) {
  const text = { corroborated: "✓ Corroborated", listed: "Listed", needs_review: "⚠ Needs review" }[level];
  const title = {
    corroborated: "Confirmed by two independent patient organisations, the NPI registry, or a trial registry.",
    listed: "On one patient-organisation list. Not independently confirmed yet.",
    needs_review: "A source flags this listing as possibly out of date (e.g. retired, moved, or unconfirmed).",
  }[level];
  return (
    <span className={`badge ${level}`} title={title}>
      {text}
    </span>
  );
}

export function TreatmentPills({
  treatments,
  site,
  highlight = [],
}: {
  treatments: { code: string; site: Site; best: keyof typeof EVIDENCE }[];
  site?: Site | "both";
  highlight?: string[];
}) {
  const shown = treatments
    .filter((t) => !site || site === "both" || t.site === site)
    .filter((t) => TREATMENT_BY_CODE[t.code])
    .sort((a, b) => Number(highlight.includes(b.code)) - Number(highlight.includes(a.code)) || EVIDENCE[a.best].rank - EVIDENCE[b.best].rank);
  return (
    <div className="pills">
      {shown.map((t) => (
        <span
          key={`${t.code}:${t.site}`}
          className={`pill ${t.site} ev-${t.best}`}
          title={`${TREATMENT_BY_CODE[t.code].label} for ${t.site === "hand" ? "hands" : "feet"}. ${EVIDENCE[t.best].long}`}
        >
          {t.site === "foot" ? "🦶 " : ""}
          {TREATMENT_BY_CODE[t.code].label}
          {t.best !== "listed" && <span className="ev">· {EVIDENCE[t.best].label}</span>}
        </span>
      ))}
    </div>
  );
}

export default function ProviderCard({
  p,
  site,
  tx,
}: {
  p: ProviderSummary;
  site?: Site | "both";
  tx: string[];
}) {
  const loc = p.nearest;
  const who = [p.honorific, p.name].filter(Boolean).join(" ");
  return (
    <article className="panel card">
      <div className="card-top">
        <div>
          <h3>
            <Link href={`/p/${p.id}`}>{p.kind === "clinician" ? who : p.name}</Link>
            {p.credential && <span className="muted" style={{ fontWeight: 400 }}>, {p.credential}</span>}
          </h3>
          <div className="sub">
            {[p.specialty_label, loc?.practice && loc.practice !== p.name ? loc.practice : null].filter(Boolean).join(" · ")}
          </div>
          <div className="sub">
            {loc ? placeLine(loc) : "Location unknown"}
            {loc && <> · {countryName(loc.country)}</>}
            {p.location_count > 1 && <> · +{p.location_count - 1} more location{p.location_count > 2 ? "s" : ""}</>}
          </div>
        </div>
        {p.distance_km != null && <div className="distance">{formatDistance(p.distance_km, loc?.country)}</div>}
      </div>
      <TreatmentPills treatments={p.treatments} site={site} highlight={tx} />
      <div className="meta-row">
        <VerificationBadge level={p.verification_level} />
        {p.early_stage && <span className="badge early">Treats early-stage</span>}
        {p.mention_count > 0 && (
          <span className="badge mention" title="Mentions on r/DupuytrenDisease">
            💬 {p.mention_count} patient mention{p.mention_count > 1 ? "s" : ""}
          </span>
        )}
        {p.flags.includes("video_consult") && <span className="badge listed">Video consults</span>}
        {p.kind === "trial_site" && <span className="badge early">Recruiting trial</span>}
      </div>
    </article>
  );
}
