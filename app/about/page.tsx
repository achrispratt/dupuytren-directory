import type { Metadata } from "next";
import Link from "next/link";
import { db } from "@/lib/db";
import { EVIDENCE, TREATMENTS } from "@/lib/treatments";

export const metadata: Metadata = { title: "How this works" };
export const dynamic = "force-dynamic";

export default async function About() {
  const sources = await db()<{ id: string; label: string; url: string; kind: string; page_modified: string | null; n: number }>(
    `select s.*, (select count(*) from provider_sources ps where ps.source_id = s.id)::int as n
     from sources s order by n desc`,
  );
  return (
    <div className="prose" style={{ margin: "24px 0 40px" }}>
      <h1>How this directory works</h1>
      <p>
        People with Dupuytren&apos;s contracture and Ledderhose disease keep asking the same question: <i>who near me
        actually offers the treatment I want?</i> Radiation for early disease, steroid injections, needle release,
        Xiaflex, a podiatrist who has seen Ledderhose before. The answers are scattered across patient-organisation
        lists, forum threads and registries. This site pulls them together, keeps track of where each fact came from,
        and lets you filter by treatment.
      </p>

      <h2>Where listings come from</h2>
      <ul>
        {sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noopener noreferrer">
              {s.label}
            </a>{" "}
            <span className="muted">
              ({s.n} listing{s.n === 1 ? "" : "s"}
              {s.page_modified ? `, page updated ${String(s.page_modified).slice(0, 10)}` : ""})
            </span>
          </li>
        ))}
      </ul>
      <p>
        We never add a doctor based only on a Reddit comment. Reddit mentions are attached to doctors that a list or
        registry already names, and doctors patients mention often are queued for manual checking.
      </p>

      <h2>How sure are we?</h2>
      <p>Each treatment on a listing carries its evidence:</p>
      <div className="legend">
        {(Object.keys(EVIDENCE) as (keyof typeof EVIDENCE)[]).map((k) => (
          <div key={k}>
            <span className={`pill hand ev-${k}`}>{EVIDENCE[k].label}</span> {EVIDENCE[k].long}
          </div>
        ))}
      </div>
      <p style={{ marginTop: 12 }}>And each listing has an overall status:</p>
      <ul>
        <li>
          <span className="badge corroborated">✓ Corroborated</span> named by two independent patient organisations,
          matched to an active record in the US NPI registry, or a registered trial site.
        </li>
        <li>
          <span className="badge listed">Listed</span> on one patient-organisation list, not yet independently
          confirmed.
        </li>
        <li>
          <span className="badge needs_review">⚠ Needs review</span> a source says the doctor may have retired or moved,
          the only source is out of date, or a US doctor has no unique NPI match.
        </li>
      </ul>

      <h2>Treatments</h2>
      <ul>
        {TREATMENTS.filter((t) => t.code !== "clinical_trial").map((t) => (
          <li key={t.code}>
            <b>{t.label}</b>: {t.blurb}
          </li>
        ))}
      </ul>

      <h2>Limits</h2>
      <ul>
        <li>Patient-organisation lists are volunteer-maintained and some entries are years old.</li>
        <li>Being listed is not an endorsement, and absence doesn&apos;t mean a doctor won&apos;t help you.</li>
        <li>Map pins for some listings are approximate (city level).</li>
        <li>This is not medical advice. Talk to a specialist about what suits your stage of disease.</li>
      </ul>
      <p>
        Spotted something wrong, or know a doctor we&apos;re missing? <Link href="/suggest">Tell us</Link>. Every
        submission is reviewed before it changes a listing.
      </p>
    </div>
  );
}
