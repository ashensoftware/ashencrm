import { describe, expect, test, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import * as api from "../api";
import { useProspects } from "./useProspects";

describe("useProspects", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "fetchCatalog").mockResolvedValue([]);
    vi.spyOn(api, "normalizeCategories").mockResolvedValue(undefined);
    vi.spyOn(api, "fetchProspects").mockResolvedValue([]);
    vi.spyOn(api, "fetchHexagons").mockResolvedValue([]);
    vi.spyOn(api, "fetchStats").mockResolvedValue({});
  });

  test("initial refresh", async () => {
    const { result } = renderHook(() => useProspects());
    await waitFor(() => expect(api.fetchProspects).toHaveBeenCalled());
    expect(result.current.prospects).toEqual([]);
  });

  test("refresh onlyList skips hex and stats", async () => {
    const { result } = renderHook(() => useProspects());
    await waitFor(() => expect(api.fetchProspects).toHaveBeenCalled());
    vi.mocked(api.fetchProspects).mockClear();
    vi.mocked(api.fetchHexagons).mockClear();
    vi.mocked(api.fetchStats).mockClear();
    await result.current.refresh(true);
    expect(api.fetchProspects).toHaveBeenCalled();
    expect(api.fetchHexagons).not.toHaveBeenCalled();
    expect(api.fetchStats).not.toHaveBeenCalled();
  });
});
