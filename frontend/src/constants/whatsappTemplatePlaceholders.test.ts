import { describe, expect, test } from "vitest";
import { WHATSAPP_TEMPLATE_PLACEHOLDERS } from "./whatsappTemplatePlaceholders";

describe("WHATSAPP_TEMPLATE_PLACEHOLDERS", () => {
  test("has expected keys for backend parity", () => {
    const keys = WHATSAPP_TEMPLATE_PLACEHOLDERS.map((p) => p.key);
    expect(keys).toContain("name");
    expect(keys).toContain("maps_url");
    expect(WHATSAPP_TEMPLATE_PLACEHOLDERS.every((p) => p.description.length > 0)).toBe(true);
  });
});
