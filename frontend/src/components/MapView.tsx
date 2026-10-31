import { useEffect } from "react";
import { Circle, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { SearchResponse, Zone } from "../types";

export const growthColor = (p: number) => `hsl(${Math.round(p * 1.2)}, 62%, 40%)`;

function FlyTo({ zone }: { zone?: Zone }) {
  const map = useMap();
  useEffect(() => {
    if (zone) map.flyTo([zone.lat, zone.lon], 9, { duration: 0.8 });
  }, [zone, map]);
  return null;
}

interface Props { zones: Zone[]; selectedId: string; onSelect: (id: string) => void; result: SearchResponse | null }

export default function MapView({ zones, selectedId, onSelect, result }: Props) {
  const selected = zones.find((z) => z.id === selectedId);
  return (
    <MapContainer center={[43.45, 11.1]} zoom={8} scrollWheelZoom className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FlyTo zone={selected} />
      {zones.map((z) => {
        const isSel = z.id === selectedId;
        const pct = isSel && result && result.zone.id === z.id ? result.growth.percentage : null;
        const color = pct !== null ? growthColor(pct) : isSel ? "#b4761b" : "#4a6b45";
        return (
          <Circle
            key={`${z.id}-${pct}`} center={[z.lat, z.lon]} radius={z.radius_km * 1000}
            pathOptions={{ color, weight: isSel ? 3 : 1.5, fillColor: color, fillOpacity: pct !== null ? 0.45 : isSel ? 0.25 : 0.12 }}
            eventHandlers={{ click: () => onSelect(z.id) }}
          >
            <Tooltip permanent={isSel} direction="center" className="zone-tip">
              {z.name}{pct !== null ? ` · ${pct}%` : ""}
            </Tooltip>
          </Circle>
        );
      })}
    </MapContainer>
  );
}
