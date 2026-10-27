"use client";

import dynamic from "next/dynamic";

// Leaflet touches `window`, so it only renders in the browser.
const ResultsMap = dynamic(() => import("./ResultsMap"), {
  ssr: false,
  loading: () => <div className="map" aria-hidden style={{ background: "var(--surface-2)" }} />,
});

export default ResultsMap;
