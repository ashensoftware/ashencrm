import { describe, expect, test } from "vitest";
import type { Prospect } from "../types";
import {
  mapStatusToColor,
  mapStatusToInfo,
  mapStatusToLabel,
  mapClientStageToColor,
  mapClientStageToLabel,
} from "../utils/statusMapper";

describe("mapStatusToInfo", () => {
  test("null prospect", () => {
    expect(mapStatusToInfo(null).label).toBe("DESCONOCIDO");
  });

  test("contacted flag uses contacted style", () => {
    const p = { name: "a", category: "c", status: "scraped", is_contacted: true } as Prospect;
    expect(mapStatusToInfo(p).class).toBe("contacted");
  });

  test("status contacted", () => {
    const p = { name: "a", category: "c", status: "contacted" } as Prospect;
    expect(mapStatusToInfo(p).class).toBe("contacted");
  });

  test("known status", () => {
    const p = { name: "a", category: "c", status: "demo_created" } as Prospect;
    expect(mapStatusToInfo(p).label).toContain("DEMO");
  });

  test("unknown status fallback", () => {
    const p = { name: "a", category: "c", status: "custom_x" } as Prospect;
    expect(mapStatusToInfo(p).label).toBe("CUSTOM_X");
    expect(mapStatusToInfo(p).class).toBe("unknown");
  });

  test("empty string status uses unknown map branch", () => {
    const p = { name: "a", category: "c", status: "" } as Prospect;
    const info = mapStatusToInfo(p);
    expect(info.class).toBe("unknown");
  });
});

describe("mapStatusToColor", () => {
  test("known keys", () => {
    expect(mapStatusToColor("waiting")).toBe("#58a6ff");
    expect(mapStatusToColor("client_won")).toBe("#10b981");
  });

  test("fallback", () => {
    expect(mapStatusToColor("other")).toBe("#94a3b8");
    expect(mapStatusToColor()).toBe("#94a3b8");
  });
});

describe("mapStatusToLabel", () => {
  test("returns correct label for valid status", () => {
    expect(mapStatusToLabel("scraped")).toBe("Potencial");
    expect(mapStatusToLabel("demo_created")).toBe("Demo Lista");
  });

  test("returns fallback format for unknown status", () => {
    expect(mapStatusToLabel("unknown_status")).toBe("unknown_status");
    expect(mapStatusToLabel()).toBe("—");
  });
});

describe("client stage mappers", () => {
  test("colors and labels", () => {
    expect(mapClientStageToColor("quote_sent")).toBe("#8b5cf6");
    expect(mapClientStageToColor()).toBe("#94a3b8");
    expect(mapClientStageToLabel("meetings")).toBe("Reuniones");
    expect(mapClientStageToLabel("unknown_stage")).toBe("unknown stage");
    expect(mapClientStageToLabel()).toBe("—");
  });
});
