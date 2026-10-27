"use server";

import { createHash } from "node:crypto";
import { headers } from "next/headers";
import { db } from "@/lib/db";
import { TREATMENT_BY_CODE } from "@/lib/treatments";

export interface SubmitState {
  ok: boolean;
  message: string;
}

const KINDS = ["new_provider", "correction", "experience"] as const;
const str = (f: FormData, k: string, max = 2000) => String(f.get(k) ?? "").trim().slice(0, max);

export async function submit(_prev: SubmitState, form: FormData): Promise<SubmitState> {
  if (str(form, "website_url")) return { ok: true, message: "Thanks!" }; // honeypot: bots fill every field
  const kind = str(form, "kind") as (typeof KINDS)[number];
  if (!KINDS.includes(kind)) return { ok: false, message: "Pick what you're telling us about." };

  const providerId = str(form, "provider_id", 120) || null;
  const treatments = form.getAll("tx").map(String).filter((t) => TREATMENT_BY_CODE[t]);
  const payload = {
    name: str(form, "name", 200),
    practice: str(form, "practice", 200),
    location: str(form, "location", 200),
    website: str(form, "website", 300),
    site: str(form, "site", 10),
    treatments,
    early_stage: str(form, "early_stage", 10),
    details: str(form, "details", 4000),
    when: str(form, "when", 40),
  };
  if (kind === "new_provider" && (!payload.name || !payload.location)) {
    return { ok: false, message: "Please give the doctor's name and where they practise." };
  }
  if (kind !== "new_provider" && !providerId) return { ok: false, message: "Missing which listing this is about." };
  if (!payload.details && treatments.length === 0) {
    return { ok: false, message: "Please tell us a little about it." };
  }

  const h = await headers();
  const ip = (h.get("x-forwarded-for") ?? "").split(",")[0].trim() || "unknown";
  const ipHash = createHash("sha256").update(ip + (process.env.ADMIN_TOKEN ?? "salt")).digest("hex").slice(0, 32);
  const [{ n }] = await db()<{ n: number }>(
    "select count(*)::int as n from submissions where ip_hash = $1 and created_at > now() - interval '1 hour'",
    [ipHash],
  );
  if (n >= 10) return { ok: false, message: "Thanks, we've had a lot from you this hour. Please try again later." };

  await db()(
    "insert into submissions (kind, provider_id, payload, contact, ip_hash) values ($1, $2, $3, $4, $5)",
    [kind, providerId, JSON.stringify(payload), str(form, "contact", 200) || null, ipHash],
  );
  return {
    ok: true,
    message: "Thank you. A volunteer will review this before anything changes on the site.",
  };
}
