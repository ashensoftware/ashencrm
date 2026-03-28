import { describe, expect, test } from "vitest";
import { createDefaultFilters } from "./filters";

describe("createDefaultFilters", () => {
  test("empty string fields", () => {
    expect(createDefaultFilters()).toEqual({
      status: "",
      contacted: "",
      has_instagram: "",
      category: "",
      name: "",
    });
  });
});
