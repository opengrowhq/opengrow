import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Component/interaction test harness (jsdom). The pure-logic `*.test.mjs`
// suites keep running under `node --test` via the `test` script; Vitest only
// picks up `*.test.tsx` so the two harnesses don't overlap.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.tsx"],
    css: false,
  },
});
