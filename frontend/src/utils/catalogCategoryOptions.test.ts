import { describe, expect, test } from "vitest";
import { catalogCategoryOptions } from "./catalogCategoryOptions";
import type { CatalogItem } from "../types";

describe("catalogCategoryOptions", () => {
  const cat: CatalogItem[] = [{ name: "gym", label: "Gimnasio" }];

  test("empty current returns catalog", () => {
    expect(catalogCategoryOptions(cat, undefined)).toEqual(cat);
    expect(catalogCategoryOptions(cat, "  ")).toEqual(cat);
  });

  test("current in catalog unchanged", () => {
    expect(catalogCategoryOptions(cat, "gym")).toEqual(cat);
  });

  test("appends historic when missing", () => {
    const out = catalogCategoryOptions(cat, "old_cat");
    expect(out).toHaveLength(2);
    expect(out[1]).toEqual({ name: "old_cat", label: "old_cat (histórico)" });
  });
});
