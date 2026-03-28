import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet.markercluster";
import type { Prospect } from "../types";
import type { Hexagon } from "../types";
import { mapStatusToColor } from "../utils";
import { LABELS, MAP_CENTER, MAP_ZOOM } from "../constants";

interface Props {
  prospects: Prospect[];
  hexagons: Hexagon[];
  selectedProspect: Prospect | null;
  onHexClick: (hex: unknown, latlng: { lat: number; lng: number }) => void;
}

export function MapView({ prospects, hexagons, selectedProspect, onHexClick }: Props) {
  const mapRef = useRef<L.Map | null>(null);
  // @ts-ignore - leaflet.markercluster types not in @types/leaflet
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);
  const hexLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    const map = L.map("map").setView([MAP_CENTER.lat, MAP_CENTER.lng], MAP_ZOOM);
    mapRef.current = map;

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "",
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    // @ts-ignore - leaflet.markercluster extension
    const cluster = L.markerClusterGroup({
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
    });
    map.addLayer(cluster);
    clusterRef.current = cluster;

    const hexLayer = L.layerGroup().addTo(map);
    hexLayerRef.current = hexLayer;

    return () => {
      map.remove();
      mapRef.current = null;
      clusterRef.current = null;
      hexLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cluster = clusterRef.current;
    if (!cluster) return;
    cluster.clearLayers();

    prospects.forEach((p) => {
      if (!p.latitude || !p.longitude) return;
      const color = mapStatusToColor(p.status);
      const marker = L.circleMarker([p.latitude, p.longitude], {
        radius: 8,
        fillColor: color,
        color: "#fff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85,
      });
      const statusLabel = (p.status || "N/A").replace("_", " ").toUpperCase();
      const scoreHtml = p.lead_score != null ? `<br><small>Score: ${p.lead_score}</small>` : "";
      marker.bindPopup(
        `<div class="map-popup">
          <strong>${escapeHtml(p.name)}</strong>
          <p>${escapeHtml(p.address || "")}</p>
          <p><span class="popup-status">${statusLabel}</span>${scoreHtml}</p>
          ${p.maps_url ? `<a href="${p.maps_url}" target="_blank" rel="noopener">${LABELS.MAP_VIEW}</a>` : ""}
        </div>`
      );
      cluster.addLayer(marker);
    });
  }, [prospects]);

  useEffect(() => {
    const hexLayer = hexLayerRef.current;
    if (!hexLayer) return;
    hexLayer.clearLayers();

    hexagons.forEach((hex) => {
      const isCompleted = hex.status === "completed";
      const isEmpty = hex.status === "empty";
      let color = "#8b5cf6";
      if (isCompleted) color = "#64748b";
      if (isEmpty) color = "rgba(100, 116, 139, 0.4)";
      const polygon = L.polygon(hex.boundary as unknown as L.LatLngExpression[][], {
        color,
        weight: isEmpty ? 1 : 2,
        fillColor: color,
        fillOpacity: isEmpty ? 0.05 : isCompleted ? 0.25 : 0.12,
        dashArray: isCompleted ? "" : "5, 5",
      });
      let infoMsg = `Área: ${hex.count} leads (${hex.processed_count} revisados)`;
      if (isCompleted) infoMsg = `Completado (${hex.count} leads)`;
      if (isEmpty) infoMsg = `Zona sin explorar — Clic para scrapear`;
      polygon.bindTooltip(infoMsg, { sticky: true });
      polygon.on("click", (e) => onHexClick(hex, e.latlng));
      hexLayer.addLayer(polygon);
    });
  }, [hexagons, onHexClick]);

  useEffect(() => {
    if (!selectedProspect?.latitude || !selectedProspect?.longitude || !mapRef.current || !clusterRef.current) return;
    const map = mapRef.current;
    map.setView([selectedProspect.latitude, selectedProspect.longitude], 18, { animate: true });
    clusterRef.current.eachLayer((layer: any) => {
      const m = layer as L.CircleMarker;
      const ll = m.getLatLng?.();
      if (ll?.lat === selectedProspect.latitude && ll?.lng === selectedProspect.longitude) {
        m.openPopup?.();
      }
    });
  }, [selectedProspect]);

  return <div id="map" />;
}

function escapeHtml(str: string) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
