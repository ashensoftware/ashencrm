/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: resolve(__dirname, "../frontend/dist"),
    emptyDir: true,
  },
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/utils/**/*.{ts,tsx}", "src/constants/**/*.ts", "src/hooks/**/*.ts"],
      // useAppActions: mejor con tests e2e; index.ts solo reexporta.
      exclude: ["src/**/*.test.*", "src/hooks/useAppActions.ts", "src/utils/index.ts"],
      thresholds: {
        lines: 100,
        functions: 100,
        branches: 90,
        statements: 100,
      },
    },
  },
});
