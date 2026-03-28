import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebounce } from "./useDebounce";

describe("useDebounce", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  test("updates after delay", () => {
    const { result, rerender } = renderHook(
      ({ v, d }: { v: string; d: number }) => useDebounce(v, d),
      { initialProps: { v: "a", d: 100 } }
    );
    expect(result.current).toBe("a");
    rerender({ v: "b", d: 100 });
    expect(result.current).toBe("a");
    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe("b");
  });
});
