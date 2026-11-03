import { defineConfig } from "vitest/config";
import path from "node:path";

/**
 * Minimal vitest config: jsdom environment (needed by the zustand `persist`
 * middleware, which reads/writes `localStorage`, and by any future
 * @testing-library/react component tests) plus the same `@/*` path alias
 * declared in tsconfig.json, resolved manually since vitest doesn't read
 * tsconfig `paths` on its own without an extra plugin.
 */
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "server-only": path.resolve(__dirname, "tests/stubs/server-only.ts"),
    },
  },
});
