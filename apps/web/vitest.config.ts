import { defineConfig } from "vitest/config";
import { join } from "node:path";

export default defineConfig({
  resolve: {
    alias: [
      {
        find: "@livecho/protocol/browser",
        replacement: join(import.meta.dirname, "../../packages/protocol/src/browser.ts"),
      },
    ],
  },
  test: {
    environment: "happy-dom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
  },
});
