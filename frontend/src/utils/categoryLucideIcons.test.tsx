import { describe, expect, test } from "vitest";
import { render } from "@testing-library/react";
import {
  CATEGORY_ICON_PICKER,
  LucideCategoryIcon,
  getCategoryIconLabel,
} from "./categoryLucideIcons";

describe("categoryLucideIcons", () => {
  test("picker has ids", () => {
    expect(CATEGORY_ICON_PICKER.length).toBeGreaterThan(5);
    expect(CATEGORY_ICON_PICKER[0].Icon).toBeDefined();
  });

  test("getCategoryIconLabel", () => {
    expect(getCategoryIconLabel("Coffee")).toBe("Café");
    expect(getCategoryIconLabel("missing")).toBeUndefined();
  });

  test("LucideCategoryIcon known id", () => {
    const { container } = render(<LucideCategoryIcon iconId="Coffee" />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  test("LucideCategoryIcon fallback circle", () => {
    const { container } = render(<LucideCategoryIcon iconId="nope" />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  test("LucideCategoryIcon no id", () => {
    const { container } = render(<LucideCategoryIcon />);
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
