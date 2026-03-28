import { describe, expect, test } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useModals } from "./useModals";

describe("useModals", () => {
  test("alert flow", async () => {
    const { result } = renderHook(() => useModals());
    let p: Promise<void>;
    await act(async () => {
      p = result.current.showAlert("T", "M");
    });
    expect(result.current.modal).toBe("alert");
    await act(async () => {
      result.current.closeAlert();
    });
    await p!;
  });

  test("prompt resolve and cancel", async () => {
    const { result } = renderHook(() => useModals());
    let p: Promise<string | null>;
    await act(async () => {
      p = result.current.showPrompt("T", "M", "d", [{ name: "a", label: "A" }]);
    });
    expect(result.current.modal).toBe("prompt");
    await act(async () => {
      result.current.resolvePrompt("ok");
    });
    await expect(p!).resolves.toBe("ok");

    let p2: Promise<string | null>;
    await act(async () => {
      p2 = result.current.showPrompt("T2", "M2");
    });
    await act(async () => {
      result.current.cancelPrompt();
    });
    await expect(p2!).resolves.toBeNull();
  });
});
