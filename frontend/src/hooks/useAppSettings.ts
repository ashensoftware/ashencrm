import { useCallback, useEffect, useState } from "react";
import { fetchAdminSettings } from "../api";
import type { AppSettings } from "../types";

export function useAppSettings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);

  const reload = useCallback(async () => {
    try {
      setSettings(await fetchAdminSettings());
    } catch {
      setSettings(null);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { settings, reload };
}
