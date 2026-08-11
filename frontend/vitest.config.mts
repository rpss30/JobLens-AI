import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Mirrors the "@/*" path alias in tsconfig.json.
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    // Server Components and Server Actions are exercised by the production
    // stack check in CI, not here; these tests cover client units.
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    restoreMocks: true,
  },
});
