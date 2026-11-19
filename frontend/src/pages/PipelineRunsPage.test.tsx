import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineRunsPage } from "./PipelineRunsPage";

describe("PipelineRunsPage", () => {
  test("shows the real-status copy and the start button", () => {
    render(<PipelineRunsPage />);
    expect(screen.getByRole("heading", { name: "Ejecuciones" })).toBeTruthy();
    expect(screen.getByText(/No hay un porcentaje inventado/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ejecutar pipeline" })).toBeTruthy();
  });
});
