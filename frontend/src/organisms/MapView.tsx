import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet.markercluster";
import type { Prospect } from "../types";
import type { Hexagon } from "../types";
import { mapClientStageToColor, mapClientStageToLabel, mapStatusToColor } from "../utils";
import { LABELS, MAP_CENTER as DEFAULT_MAP_CENTER, MAP_ZOOM as DEFAULT_MAP_ZOOM } from "../constants";

interface Props {
  prospects: Prospect[];
  hexagons: Hexagon[];
  selectedProspect: Prospect | null;
  onHexClick: (hex: unknown, latlng: { lat: number; lng: number }) => void;
  mapCenter?: { lat: number; lng: number };
  mapZoom?: number;
  /** Misma rejilla y estilo que leads; solo cambian marcadores (clientes) y clics en hexágonos. */
  variant?: "leads" | "clients";
}

export function MapView({
  prospects,
  hexagons,
  selectedProspect,
  onHexClick,
  mapCenter,
  mapZoom,
  variant = "leads",
}: Props) {
  const mapRef = useRef<L.Map | null>(null);
  // @ts-ignore - leaflet.markercluster types not in @types/leaflet
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);
  const hexLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    const center = mapCenter ?? DEFAULT_MAP_CENTER;
    const zoom = mapZoom ?? DEFAULT_MAP_ZOOM;
    const map = L.map("map").setView([center.lat, center.lng], zoom);
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
    const map = mapRef.current;
    if (!map) return;
    const center = mapCenter ?? DEFAULT_MAP_CENTER;
    const zoom = mapZoom ?? DEFAULT_MAP_ZOOM;
    map.setView([center.lat, center.lng], zoom);
  }, [mapCenter?.lat, mapCenter?.lng, mapZoom]);

  useEffect(() => {
    const cluster = clusterRef.current;
    if (!cluster) return;
    cluster.clearLayers();

    const isClients = variant === "clients";
    prospects.forEach((p) => {
      if (!p.latitude || !p.longitude) return;
      const color = isClients ? mapClientStageToColor(p.status) : mapStatusToColor(p.status);
      const marker = L.circleMarker([p.latitude, p.longitude], {
        radius: 8,
        fillColor: color,
        color: "#fff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85,
      });
      const statusLabel = isClients
        ? mapClientStageToLabel(p.status)
        : (p.status || "N/A").replace("_", " ").toUpperCase();
      const scoreHtml =
        !isClients && p.lead_score != null ? `<br><small>Score: ${p.lead_score}</small>` : "";
      const addrOrCat = isClients
        ? escapeHtml(p.category || "")
        : escapeHtml(p.address || "");
      const mapsLink = p.maps_url
        ? `<a href="${p.maps_url}" target="_blank" rel="noopener">${LABELS.MAP_VIEW}</a>`
        : "";
      const pipelineLink = isClients
        ? `<p><a href="/clientes/pipeline">Ver pipeline de clientes</a></p>`
        : "";
      marker.bindPopup(
        `<div class="map-popup">
          <strong>${escapeHtml(p.name)}</strong>
          ${addrOrCat ? `<p>${addrOrCat}</p>` : ""}
          <p><span class="popup-status">${escapeHtml(statusLabel)}</span>${scoreHtml}</p>
          ${mapsLink}
          ${pipelineLink}
        </div>`
      );
      cluster.addLayer(marker);
    });
  }, [prospects, variant]);

  useEffect(() => {
    const hexLayer = hexLayerRef.current;
    if (!hexLayer) return;
    hexLayer.clearLayers();

    const isClients = variant === "clients";
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
      if (isEmpty)
        infoMsg = isClients
          ? `Zona sin explorar — Para scrapear, abre Leads → Explorar mapa`
          : `Zona sin explorar — Clic para scrapear`;
      if (isClients && !isEmpty && !isCompleted)
        infoMsg = `Captación: ${hex.count} leads (${hex.processed_count} revisados)`;
      polygon.bindTooltip(infoMsg, { sticky: true });
      polygon.on("click", (e) => {
        if (isClients) return;
        onHexClick(hex, e.latlng);
      });
      hexLayer.addLayer(polygon);
    });
  }, [hexagons, onHexClick, variant]);

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
