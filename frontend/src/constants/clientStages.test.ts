import { describe, expect, test } from "vitest";
import { STAGE_COLUMNS, clientStageLabel } from "./clientStages";

describe("clientStages", () => {
  test("clientStageLabel known", () => {
    expect(clientStageLabel("quote_sent")).toBe("Cotización");
  });

  test("clientStageLabel passthrough", () => {
    expect(clientStageLabel("custom")).toBe("custom");
  });

  test("STAGE_COLUMNS shape", () => {
    expect(STAGE_COLUMNS.length).toBeGreaterThan(0);
    expect(STAGE_COLUMNS[0]).toHaveProperty("stage");
  });
});
