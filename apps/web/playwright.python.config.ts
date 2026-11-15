import { defineConfig } from "@playwright/test";

/**
 * Cross-stack E2E: Issue #11 production shell against the real Issue #9
 * Python `fixture_timeline` backend (same-origin static + /api/viewer/ws).
 *
 * Distinct from playwright.config.ts, which still uses the Node fixture double.
 * No audio, MLX, worker, or live Bilibili traffic.
 */
const SCRIPT = "bash scripts/python-fixture-server.sh";

function server(
  port: number,
  extra: string[],
): { command: string; url: string; reuseExistingServer: boolean; timeout: number } {
  return {
    command: `${SCRIPT} --port ${port} ${extra.join(" ")}`,
    url: `http://127.0.0.1:${port}/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  };
}

export default defineConfig({
  testDir: "tests/e2e-python",
  timeout: 90_000,
  expect: { timeout: 25_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8811",
  },
  webServer: [
    // One Python process per scenario so shared ports are not drained by earlier tests.
    // Python fixture admission floor is 3.5s/segment with partials (60s cap).
    server(8811, ["--segments", "12", "--interval-ms", "2500"]),
    server(8812, ["--segments", "8", "--interval-ms", "2500", "--stop-at", "3"]),
    server(8813, ["--segments", "8", "--interval-ms", "2500", "--delete-at", "3"]),
    server(8814, ["--segments", "8", "--interval-ms", "2500", "--fail-at", "3"]),
    server(8815, ["--segments", "8", "--interval-ms", "2500", "--close-at", "2"]),
    server(8816, ["--segments", "8", "--interval-ms", "2500", "--no-partials"]),
    server(8817, ["--segments", "8", "--interval-ms", "2500"]),
    server(8818, ["--segments", "8", "--interval-ms", "2500"]),
  ],
  projects: [{ name: "chromium-python", use: { browserName: "chromium" } }],
});
