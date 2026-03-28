import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import * as api from "../api";
import { POLL_INTERVAL } from "../constants";
import { useScanner } from "./useScanner";

describe("useScanner", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  test("polls until ERROR", async () => {
    vi.spyOn(api, "fetchScrapeLogs")
      .mockResolvedValueOnce(["x"])
      .mockResolvedValueOnce(["[t] ERROR"]);
    const onComplete = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() => useScanner());
    await act(async () => {
      result.current.start(onComplete);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    expect(result.current.active).toBe(false);
    expect(onComplete).toHaveBeenCalled();
  });

  test("polls until FINALIZADO", async () => {
    vi.spyOn(api, "fetchScrapeLogs")
      .mockResolvedValueOnce(["[t] ok"])
      .mockResolvedValueOnce(["[t] FINALIZADO"]);
    const onComplete = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() => useScanner());
    await act(async () => {
      result.current.start(onComplete);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    expect(result.current.active).toBe(false);
    expect(onComplete).toHaveBeenCalled();
  });

  test("start clears existing interval", async () => {
    vi.spyOn(api, "fetchScrapeLogs").mockResolvedValue(["[t] ok"]);
    const { result } = renderHook(() => useScanner());
    await act(async () => {
      result.current.start();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    await act(async () => {
      result.current.start();
    });
    expect(api.fetchScrapeLogs).toHaveBeenCalled();
  });

  test("minimize and restore", () => {
    const { result } = renderHook(() => useScanner());
    act(() => result.current.minimize());
    expect(result.current.minimized).toBe(true);
    act(() => result.current.restore());
    expect(result.current.minimized).toBe(false);
  });

  test("lastLog strips prefix", async () => {
    vi.spyOn(api, "fetchScrapeLogs").mockResolvedValue(["[2024-01-01] hello"]);
    const { result } = renderHook(() => useScanner());
    await act(async () => {
      result.current.start();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    expect(result.current.lastLog).toBe("hello");
  });
});
