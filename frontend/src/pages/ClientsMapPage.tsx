import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchClientMapMarkers, fetchClients, fetchHexagons } from "../api";
import { useAppSettings } from "../hooks/useAppSettings";
import { MapView } from "../organisms/MapView";
import type { Client, ClientMapMarker, Hexagon, Prospect } from "../types";

function markersToProspects(markers: ClientMapMarker[]): Prospect[] {
  return markers.map((m) => ({
    name: m.display_name,
    category: m.category,
    latitude: m.latitude,
    longitude: m.longitude,
    status: m.stage,
    maps_url: m.maps_url || undefined,
    client_id: m.id,
  }));
}

export function ClientsMapPage() {
  const { settings: appSettings } = useAppSettings();
  const [clients, setClients] = useState<Client[]>([]);
  const [hexagons, setHexagons] = useState<Hexagon[]>([]);
  const [mapMarkers, setMapMarkers] = useState<ClientMapMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cl, hex] = await Promise.all([fetchClients(), fetchHexagons()]);
      setClients(cl);
      setHexagons(hex);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar");
      setHexagons([]);
      setClients([]);
    }
    try {
      setMapMarkers(await fetchClientMapMarkers());
    } catch (e) {
      setMapMarkers([]);
      setError((prev) => prev ?? (e instanceof Error ? e.message : "No se pudieron cargar los marcadores del mapa"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const prospectPins = useMemo(() => markersToProspects(mapMarkers), [mapMarkers]);

  const mapCenter = appSettings
    ? { lat: appSettings.map_center_lat, lng: appSettings.map_center_lng }
    : undefined;

  return (
    <div className="clients-map-page">
      <header className="clients-map-page-header">
        <div>
          <h1>Mapa de cuentas</h1>
          <p className="clients-page-sub">
            Misma vista territorial y rejilla hexagonal que en <strong>Leads → Explorar mapa</strong>, con
            puntos solo para <strong>clientes</strong> (coordenadas del cliente o del lead vinculado).
          </p>
          <p className="clients-map-stats" aria-live="polite">
            {loading ? (
              <span>Cargando datos…</span>
            ) : (
              <>
                <strong>{clients.length}</strong> cuenta{clients.length !== 1 ? "s" : ""}
                {mapMarkers.length > 0 && (
                  <>
                    {" "}
                    · <strong>{mapMarkers.length}</strong> con ubicación en mapa
                  </>
                )}
                {clients.length === 0 && " — Aún no hay clientes registrados."}
              </>
            )}
          </p>
        </div>
      </header>

      {error && (
        <div className="clients-map-error-banner" role="alert">
          {error}
        </div>
      )}

      <section className="clients-map-canvas-wrap" aria-label="Mapa de clientes">
        <MapView
          prospects={prospectPins}
          hexagons={hexagons}
          selectedProspect={null}
          onHexClick={() => {}}
          mapCenter={mapCenter}
          mapZoom={appSettings?.map_zoom}
          variant="clients"
        />
      </section>
    </div>
  );
}
