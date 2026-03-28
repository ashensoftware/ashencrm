import { useState, useCallback, useRef } from "react";
import { fetchScrapeLogs } from "../api";
import { POLL_INTERVAL } from "../constants";

export function useScanner() {
  const [logs, setLogs] = useState<string[]>([]);
  const [active, setActive] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const onCompleteRef = useRef<(() => Promise<void>) | null>(null);

  const start = useCallback((onComplete?: () => Promise<void>) => {
    onCompleteRef.current = onComplete ?? null;
    setActive(true);
    setMinimized(false);
    if (intervalRef.current) window.clearInterval(intervalRef.current);
    intervalRef.current = window.setInterval(async () => {
      const newLogs = await fetchScrapeLogs();
      setLogs(newLogs);
      const last = newLogs[newLogs.length - 1] || "";
      if (last.includes("FINALIZADO") || last.includes("ERROR")) {
        if (intervalRef.current) window.clearInterval(intervalRef.current);
        intervalRef.current = null;
        setActive(false);
        await onCompleteRef.current?.();
      }
    }, POLL_INTERVAL);
  }, []);

  const minimize = useCallback(() => {
    setMinimized(true);
  }, []);

  const restore = useCallback(() => {
    setMinimized(false);
  }, []);

  const lastLog = logs[logs.length - 1]?.replace(/^\[.*\]\s/, "") ?? "";

  return { logs, active, minimized, lastLog, start, minimize, restore };
}
