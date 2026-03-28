import { describe, expect, test, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import * as api from "../api";
import { useAppSettings } from "./useAppSettings";

describe("useAppSettings", () => {
  beforeEach(() => vi.restoreAllMocks());

  test("loads settings", async () => {
    vi.spyOn(api, "fetchAdminSettings").mockResolvedValue({
      default_city: "X",
      default_scrape_limit: 5,
    } as Awaited<ReturnType<typeof api.fetchAdminSettings>>);
    const { result } = renderHook(() => useAppSettings());
    await waitFor(() => expect(result.current.settings?.default_city).toBe("X"));
  });

  test("sets null on error", async () => {
    vi.spyOn(api, "fetchAdminSettings").mockRejectedValue(new Error("fail"));
    const { result } = renderHook(() => useAppSettings());
    await waitFor(() => expect(result.current.settings).toBeNull());
  });
});
