import { describe, expect, test } from "vitest";
import { createDefaultFilters, createStatCardsConfig } from "./statCards";

describe("statCards", () => {
  test("createDefaultFilters", () => {
    expect(createDefaultFilters().status).toBe("");
  });

  test("createStatCardsConfig uses stats and total", () => {
    const rows = createStatCardsConfig(
      { ready: 2, demo_created: 3, contacted: 1 },
      10
    );
    expect(rows.find((r) => r.id === "total")?.value).toBe(10);
    expect(rows.find((r) => r.id === "ready")?.value).toBe(2);
    expect(rows.find((r) => r.id === "demo")?.value).toBe(3);
    expect(rows.find((r) => r.id === "contacted")?.value).toBe(1);
  });

  test("createStatCardsConfig coalesces missing stats", () => {
    const rows = createStatCardsConfig({}, 0);
    expect(rows.find((r) => r.id === "ready")?.value).toBe(0);
  });
});
