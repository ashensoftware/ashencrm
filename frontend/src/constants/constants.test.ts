import { describe, expect, test } from "vitest";
import {
  MSG,
  LABELS,
  STATUS_OPTIONS,
  IG_OPTIONS,
  CONTACT_OPTIONS,
  MAP_CENTER,
  MAP_ZOOM,
  DEFAULT_SCRAPE_LIMIT,
  DEFAULT_CITY,
  POLL_INTERVAL,
  WHATSAPP_TEMPLATES,
} from "./index";

describe("constants index", () => {
  test("MSG templates", () => {
    expect(MSG.SCRAPE_START_FAIL("x")).toContain("x");
    expect(MSG.TYPE_BORRAR("Cat")).toContain("Cat");
  });

  test("LABELS and option arrays", () => {
    expect(LABELS.TOTAL.length).toBeGreaterThan(0);
    expect(STATUS_OPTIONS[0].value).toBe("");
    expect(IG_OPTIONS.length).toBeGreaterThan(1);
    expect(CONTACT_OPTIONS.length).toBeGreaterThan(1);
  });

  test("map and scrape defaults", () => {
    expect(MAP_CENTER.lat).toBeDefined();
    expect(MAP_ZOOM).toBe(13);
    expect(DEFAULT_SCRAPE_LIMIT).toBe(20);
    expect(DEFAULT_CITY).toBe("Medellín");
    expect(POLL_INTERVAL).toBe(5000);
  });

  test("WHATSAPP_TEMPLATES", () => {
    expect(WHATSAPP_TEMPLATES.length).toBeGreaterThan(0);
    expect(WHATSAPP_TEMPLATES[0].template).toContain("{");
  });
});
