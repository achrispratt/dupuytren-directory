"use client";

import { useActionState, useState } from "react";
import { submit, type SubmitState } from "./actions";
import { TREATMENTS } from "@/lib/treatments";

export default function SuggestForm({
  providerId,
  providerName,
  initialKind,
}: {
  providerId?: string;
  providerName?: string;
  initialKind: "new_provider" | "correction" | "experience";
}) {
  const [state, action, pending] = useActionState<SubmitState, FormData>(submit, { ok: false, message: "" });
  const [kind, setKind] = useState(initialKind);
  if (state.ok) return <p className="notice info">{state.message}</p>;

  const kinds = providerId
    ? ([
        ["experience", "I was treated or seen here"],
        ["correction", "Something on this listing is wrong"],
      ] as const)
    : ([["new_provider", "Suggest a doctor or clinic"]] as const);

  return (
    <form action={action} className="form-grid">
      <input type="hidden" name="provider_id" value={providerId ?? ""} />
      <div style={{ position: "absolute", left: -9999 }} aria-hidden>
        <label>
          Leave empty <input name="website_url" tabIndex={-1} autoComplete="off" />
        </label>
      </div>
      {providerName && (
        <p>
          About: <b>{providerName}</b>
        </p>
      )}
      <div className="segmented" role="radiogroup" aria-label="What is this about">
        {kinds.map(([k, label]) => (
          <label key={k}>
            <input type="radio" name="kind" value={k} checked={kind === k} onChange={() => setKind(k)} />
            {label}
          </label>
        ))}
      </div>

      {kind === "new_provider" && (
        <>
          <label className="field">
            Doctor or clinic name *
            <input type="text" name="name" required maxLength={200} />
          </label>
          <label className="field">
            Practice / hospital
            <input type="text" name="practice" maxLength={200} />
          </label>
          <label className="field">
            Where (city, state/region, country) *
            <input type="text" name="location" required maxLength={200} />
          </label>
          <label className="field">
            Website
            <input type="text" name="website" maxLength={300} placeholder="https://" />
          </label>
        </>
      )}

      {kind !== "correction" && (
        <>
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="muted" style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 6 }}>
              For
            </legend>
            <div className="segmented">
              {[
                ["hand", "Hands"],
                ["foot", "Feet"],
                ["both", "Both"],
              ].map(([v, l]) => (
                <label key={v}>
                  <input type="radio" name="site" value={v} defaultChecked={v === "hand"} />
                  {l}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="muted" style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 6 }}>
              {kind === "experience" ? "Treatments they offered or gave you" : "Treatments they offer"}
            </legend>
            <div className="chips">
              {TREATMENTS.filter((t) => t.code !== "clinical_trial").map((t) => (
                <label className="chip" key={t.code}>
                  <input type="checkbox" name="tx" value={t.code} />
                  {t.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="field">
            Did they treat early-stage disease (before a contracture)?
            <select name="early_stage" defaultValue="">
              <option value="">Not sure</option>
              <option value="yes">Yes</option>
              <option value="no">No, they said to wait</option>
            </select>
          </label>
        </>
      )}

      {kind === "experience" && (
        <label className="field">
          When (roughly)
          <input type="text" name="when" placeholder="e.g. spring 2026" maxLength={40} />
        </label>
      )}

      <label className="field">
        {kind === "correction" ? "What's wrong, and what's right? *" : "Anything else other patients should know"}
        <textarea name="details" maxLength={4000} required={kind === "correction"} />
      </label>
      <label className="field">
        Your email (optional, only so we can ask a follow-up; never published)
        <input type="text" name="contact" maxLength={200} />
      </label>
      {state.message && <p className="notice">{state.message}</p>}
      <div>
        <button className="btn" type="submit" disabled={pending}>
          {pending ? "Sending…" : "Send"}
        </button>
      </div>
    </form>
  );
}
