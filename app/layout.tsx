import type { Metadata } from "next";
import Link from "next/link";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Dupuytren's & Ledderhose Specialist Directory", template: "%s · Dupuytren's Directory" },
  description:
    "Find doctors who treat Dupuytren's contracture and Ledderhose disease, filtered by the treatments they actually offer: radiation, steroid injection, needle release, Xiaflex, surgery and more.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand">
              <span className="brand-mark" aria-hidden>
                ✋
              </span>
              Dupuytren&apos;s &amp; Ledderhose Directory
            </Link>
            <nav className="site-nav" aria-label="Main">
              <Link href="/">Find a doctor</Link>
              <Link href="/trials">Clinical trials</Link>
              <Link href="/suggest">Suggest a doctor</Link>
              <Link href="/about">How this works</Link>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site-footer">
          <div className="wrap">
            <p>
              A patient-run directory. Listings come from patient organisations, public registries and patient reports,
              and each one shows its sources. It is not medical advice and not an endorsement: always confirm with the
              practice what they offer and whether it suits you.
            </p>
            <p>
              <Link href="/about">Sources and methodology</Link> · <Link href="/suggest">Report a correction</Link>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
