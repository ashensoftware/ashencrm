import { afterEach, describe, expect, test, vi } from "vitest";
import { accessToken, clearAccessToken, createRequest, storeAccessToken } from "./index";

describe("access token", () => {
  afterEach(() => {
    clearAccessToken();
    vi.restoreAllMocks();
  });

  test("guarda el token y lo envía como Bearer sin meterlo en la URL", async () => {
    storeAccessToken("header.payload.sig");
    expect(accessToken()).toBe("header.payload.sig");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));
    await createRequest()("/admin/settings");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/settings");
    expect(String(url)).not.toContain("header.payload.sig");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer header.payload.sig");
  });

  test("un token vacío borra la sesión", () => {
    storeAccessToken("header.payload.sig");
    storeAccessToken("   ");
    expect(accessToken()).toBe("");
  });
});
