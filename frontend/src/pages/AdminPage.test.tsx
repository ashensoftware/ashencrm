import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { AdminPage } from "./AdminPage";
import * as api from "../api";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchAdminSettings: vi.fn(),
    fetchSqlConsoleStatus: vi.fn(),
  };
});

describe("AdminPage access token", () => {
  beforeEach(() => {
    vi.mocked(api.fetchAdminSettings).mockReset();
    vi.mocked(api.fetchSqlConsoleStatus).mockReset();
  });

  test("muestra el campo de token y el aviso cuando el backend responde 401", async () => {
    vi.mocked(api.fetchAdminSettings).mockRejectedValue(new Error("AUTH_401"));
    render(
      <AdminPage
        catalog={[]}
        refreshCatalog={async () => {}}
        refreshProspects={async () => {}}
        onSettingsSaved={() => {}}
      />
    );

    expect(screen.getByLabelText(/Token de acceso/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Parametros" }));
    expect(await screen.findByText(/token de administrador/i)).toBeTruthy();
  });
});
