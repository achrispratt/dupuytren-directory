import type { Metadata } from "next";
import SuggestForm from "./SuggestForm";
import { db } from "@/lib/db";

export const metadata: Metadata = { title: "Suggest a doctor or correction" };
export const dynamic = "force-dynamic";

export default async function Suggest({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  let provider: { id: string; name: string } | undefined;
  if (sp.provider) {
    [provider] = await db()<{ id: string; name: string }>("select id, name from providers where id = $1", [sp.provider]);
  }
  const kind = provider ? (sp.kind === "correction" ? "correction" : "experience") : "new_provider";
  return (
    <div style={{ margin: "24px 0 40px" }}>
      <h1>{provider ? "Help improve this listing" : "Suggest a doctor or clinic"}</h1>
      <p className="muted prose">
        The directory is only as good as what patients share. Tell us about a doctor who treats Dupuytren&apos;s or
        Ledderhose, especially one who offers radiation, steroid injections or early-stage treatment, or who has been
        good with Ledderhose. Submissions are reviewed by a person before anything is published.
      </p>
      <div className="panel section">
        <SuggestForm providerId={provider?.id} providerName={provider?.name} initialKind={kind} />
      </div>
    </div>
  );
}
