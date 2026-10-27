// Plain-language treatment vocabulary. Codes match scripts/ingest/lib.py TREATMENTS.

export type Site = "hand" | "foot";
export type Evidence = "listed" | "trial_site" | "trial_investigator" | "patient_reported" | "inferred";

export interface TreatmentInfo {
  code: string;
  label: string;
  short: string;
  sites: Site[];
  early: boolean; // usually offered before a contracture develops
  blurb: string;
}

export const TREATMENTS: TreatmentInfo[] = [
  {
    code: "radiotherapy",
    label: "Radiation therapy",
    short: "Radiation",
    sites: ["hand", "foot"],
    early: true,
    blurb:
      "Low-dose radiotherapy (usually orthovoltage X-rays or electrons) aimed at slowing early disease: nodules and cords before a significant contracture. Widely used in Germany; less common in the US and UK.",
  },
  {
    code: "steroid_injection",
    label: "Steroid injection",
    short: "Steroid",
    sites: ["hand", "foot"],
    early: true,
    blurb:
      "Corticosteroid (e.g. triamcinolone) injected into a nodule to soften or shrink it and ease pain. Often repeated. Also used alongside needle release.",
  },
  {
    code: "needle_aponeurotomy",
    label: "Needle aponeurotomy (needle release)",
    short: "Needle",
    sites: ["hand"],
    early: false,
    blurb:
      "A needle is used to divide the cord through the skin, usually under local anaesthetic in clinic. Also called PNF or percutaneous needle fasciotomy. Quick recovery; recurrence is more common than after surgery.",
  },
  {
    code: "collagenase",
    label: "Collagenase injection (Xiaflex)",
    short: "Xiaflex",
    sites: ["hand"],
    early: false,
    blurb:
      "An enzyme injected into the cord, followed by a manipulation a day or two later to straighten the finger. Available in the US; withdrawn from Europe, Canada and Australia.",
  },
  {
    code: "fasciectomy",
    label: "Fasciectomy (open surgery)",
    short: "Surgery",
    sites: ["hand"],
    early: false,
    blurb: "Surgical removal of the diseased tissue (limited or segmental fasciectomy). Longer recovery with hand therapy.",
  },
  {
    code: "dermofasciectomy",
    label: "Dermofasciectomy",
    short: "Dermofasciectomy",
    sites: ["hand"],
    early: false,
    blurb: "Removes the diseased tissue and the overlying skin, replaced with a skin graft. Used for recurrent or aggressive disease.",
  },
  {
    code: "lipofilling",
    label: "Needle release with fat grafting",
    short: "PALF",
    sites: ["hand"],
    early: false,
    blurb: "Needle release combined with fat grafting under the skin (PALF), offered by a few surgeons.",
  },
  {
    code: "hyaluronidase_injection",
    label: "Hyaluronidase injection (Vitrase)",
    short: "Vitrase",
    sites: ["foot", "hand"],
    early: true,
    blurb:
      "An enzyme injection some podiatrists use for Ledderhose nodules, sometimes combined with steroid. Not an established treatment; evidence is patient reports.",
  },
  {
    code: "cryoablation",
    label: "Cryoablation",
    short: "Cryo",
    sites: ["foot"],
    early: false,
    blurb: "Freezing the nodule with a probe. Used by a few clinics for Ledderhose; limited long-term data.",
  },
  {
    code: "shockwave",
    label: "Shockwave therapy (ESWT)",
    short: "Shockwave",
    sites: ["foot"],
    early: true,
    blurb: "Extracorporeal shockwave therapy. Some patients report softer nodules and less pain; others find it painful and unhelpful.",
  },
  {
    code: "foot_surgery",
    label: "Plantar fibroma surgery",
    short: "Foot surgery",
    sites: ["foot"],
    early: false,
    blurb:
      "Removal of Ledderhose nodules or the plantar fascia. Usually a last resort because of high recurrence and a long recovery.",
  },
  {
    code: "orthotics",
    label: "Orthotics and offloading insoles",
    short: "Orthotics",
    sites: ["foot"],
    early: true,
    blurb: "Custom or soft insoles, sometimes with cut-outs, to take pressure off nodules when walking.",
  },
  {
    code: "foot_care",
    label: "Ledderhose foot care (podiatry)",
    short: "Podiatry",
    sites: ["foot"],
    early: true,
    blurb: "A podiatrist recommended by patients for Ledderhose. Ask which treatments they offer.",
  },
  {
    code: "ultrasound_diagnosis",
    label: "Ultrasound diagnosis",
    short: "Ultrasound",
    sites: ["foot", "hand"],
    early: true,
    blurb: "Diagnostic ultrasound to confirm a nodule is Ledderhose or Dupuytren's tissue.",
  },
  {
    code: "hand_therapy",
    label: "Hand therapy and splinting",
    short: "Therapy",
    sites: ["hand"],
    early: true,
    blurb: "Physiotherapy, massage or splinting, before or after treatment.",
  },
  {
    code: "clinical_trial",
    label: "Clinical trial site",
    short: "Trial",
    sites: ["hand", "foot"],
    early: false,
    blurb: "Currently recruiting for a registered clinical trial.",
  },
];

export const TREATMENT_BY_CODE = Object.fromEntries(TREATMENTS.map((t) => [t.code, t])) as Record<string, TreatmentInfo>;

export const EVIDENCE: Record<Evidence, { label: string; long: string; rank: number }> = {
  listed: {
    label: "Listed",
    long: "A patient organisation (International Dupuytren Society or British Dupuytren's Society) lists this provider for this treatment.",
    rank: 0,
  },
  trial_site: { label: "Trial site", long: "An open ClinicalTrials.gov study of this treatment runs here.", rank: 1 },
  trial_investigator: {
    label: "Researcher",
    long: "Named as an investigator on a ClinicalTrials.gov study of this treatment.",
    rank: 2,
  },
  patient_reported: {
    label: "Patient report",
    long: "A patient on r/DupuytrenDisease mentioned this provider alongside this treatment. Unverified.",
    rank: 3,
  },
  inferred: {
    label: "Likely",
    long: "Not listed directly. The British Dupuytren's Society notes that clinics treating Dupuytren's with radiation are likely to treat Ledderhose too. Ask before booking.",
    rank: 4,
  },
};

export const SITE_LABEL: Record<Site, string> = { hand: "Hands (Dupuytren's)", foot: "Feet (Ledderhose)" };
