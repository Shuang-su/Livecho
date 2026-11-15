import { defineConfig } from "@playwright/test";

/**
 * Every E2E server is a local fixture_timeline double (scripts/fixture-server.mjs)
 * serving the production build of the static shell from dist/. No real audio,
 * model, worker, or platform content is involved. Run `pnpm test:e2e` which
 * builds first.
 */
const DIST = "dist";

function server(
  port: number,
  extra: string[],
): { command: string; url: string; reuseExistingServer: boolean } {
  return {
    command: `node scripts/fixture-server.mjs --root ${DIST} --port ${port} ${extra.join(" ")}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: true,
  };
}

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8801",
  },
  webServer: [
    server(8801, ["--segments", "60", "--interval", "2500"]),
    server(8802, ["--segments", "10", "--stop-at", "3"]),
    server(8803, ["--segments", "10", "--delete-at", "3"]),
    server(8804, ["--segments", "10", "--fail-at", "3"]),
    server(8805, ["--segments", "10", "--close-at", "2", "--refuse-resume"]),
    server(8806, ["--segments", "10", "--interval", "2500", "--no-partials"]),
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
