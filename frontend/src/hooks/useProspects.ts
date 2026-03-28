import { useCallback, useEffect, useState } from "react";
import {
  fetchCatalog,
  fetchProspects,
  fetchStats,
  fetchHexagons,
  normalizeCategories,
} from "../api";
import { createDefaultFilters } from "../utils";
import type { Prospect, ProspectFilters } from "../types";
import type { CatalogItem } from "../types";
import type { Hexagon } from "../types";

export function useProspects() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [hexagons, setHexagons] = useState<Hexagon[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [filters, setFilters] = useState<ProspectFilters>(createDefaultFilters);

  const refresh = useCallback(async (onlyList = false) => {
    const data = await fetchProspects(filters);
    setProspects(data);
    if (!onlyList) {
      const [hexData, statsData] = await Promise.all([fetchHexagons(), fetchStats()]);
      setHexagons(hexData);
      setStats(statsData);
    }
  }, [filters]);

  const refreshCatalog = useCallback(async () => {
    const cat = await fetchCatalog();
    setCatalog(cat);
  }, []);

  useEffect(() => {
    (async () => {
      await refreshCatalog();
      await normalizeCategories();
      await refresh();
    })();
  }, [refresh, refreshCatalog]);

  return { prospects, hexagons, stats, catalog, filters, setFilters, refresh, refreshCatalog };
}
