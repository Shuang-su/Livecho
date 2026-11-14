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
    environment: "node",
    include: ["tests/stress/**/*.ts"],
    testTimeout: 180_000,
    hookTimeout: 30_000,
  },
});
