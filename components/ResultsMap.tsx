"use client";

import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

export interface Point {
  id: string;
  name: string;
  lat: number;
  lng: number;
  level: string;
}

const COLORS: Record<string, string> = { corroborated: "#1d6b3f", listed: "#1f6f62", needs_review: "#b5652b" };

function Fit({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 11 });
  }, [map, bounds]);
  return null;
}

export default function ResultsMap({
  points,
  center,
  highlight = [],
}: {
  points: Point[];
  center?: { lat: number; lng: number } | null;
  highlight?: string[];
}) {
  const hl = useMemo(() => new Set(highlight), [highlight]);
  const bounds = useMemo<LatLngBoundsExpression | null>(() => {
    const focus = points.filter((p) => hl.has(p.id));
    const use = focus.length ? focus : points;
    const pts: [number, number][] = use.map((p) => [p.lat, p.lng]);
    if (center) pts.push([center.lat, center.lng]);
    if (!pts.length) return null;
    return pts as LatLngBoundsExpression;
  }, [points, center, hl]);

  return (
    <MapContainer className="map" center={[30, 0]} zoom={2} scrollWheelZoom={false} worldCopyJump>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Fit bounds={bounds} />
      {center && (
        <CircleMarker center={[center.lat, center.lng]} radius={7} pathOptions={{ color: "#b5652b", fillOpacity: 0.9 }}>
          <Popup>You searched here</Popup>
        </CircleMarker>
      )}
      {points.map((p) => (
        <CircleMarker
          key={p.id}
          center={[p.lat, p.lng]}
          radius={hl.has(p.id) ? 7 : 4}
          pathOptions={{
            color: COLORS[p.level] ?? "#1f6f62",
            weight: hl.has(p.id) ? 2 : 1,
            fillOpacity: hl.has(p.id) ? 0.85 : 0.45,
          }}
        >
          <Popup>
            <a href={`/p/${p.id}`}>{p.name}</a>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
