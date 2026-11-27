// Invoked by the loopback Python WSS test. All caption assertions stay in memory.
import { createInterface } from "node:readline";
import { chromium, expect } from "@playwright/test";

const url = process.argv[2];
const browser = await chromium.launch();
try {
  const context = await browser.newContext({
    // The Python fixture creates a disposable self-signed TLS certificate in RAM.
    ignoreHTTPSErrors: true,
    serviceWorkers: "block",
  });
  const clients = await Promise.all(
    [{ width: 1280, height: 800 }, { width: 390, height: 844 }].map(async viewport => {
      const page = await context.newPage();
      await page.setViewportSize(viewport);
      const faults = [];
      let sockets = 0;
      page.on("pageerror", error => faults.push(error.message));
      page.on("console", message => {
        if (message.text() === "Service Worker registration blocked by Playwright") return;
        if (["error", "warning"].includes(message.type())) faults.push(message.text());
      });
      page.on("websocket", socket => {
        if (socket.url().endsWith("/api/viewer/ws")) sockets += 1;
      });
      await page.goto(url);
      return {
        page,
        checkConnection: () => {
          if (faults.length > 0) throw new Error(`Browser reported: ${faults.join(" | ")}`);
          if (sockets !== 1) throw new Error("Live rotation opened a new WebSocket");
        },
      };
    }),
  );

  const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const stage of input) {
    await Promise.all(clients.map(async ({ page, checkConnection }) => {
      const status = page.getByTestId("status-line");
      const partial = page.getByTestId("partial-row");
      const gap = page.getByTestId("gap-notice");
      const rows = page.getByTestId("final-list").locator("li");
      switch (stage) {
        case "ready":
          await expect(page).toHaveTitle(/Livecho/);
          await expect(page).toHaveURL(new URL(url).href);
          await expect(page.getByRole("heading", { name: "Livecho captions" })).toBeVisible();
          await expect(page.locator("vite-error-overlay")).toHaveCount(0);
          await expect(page.getByTestId("empty-subtitles")).toBeVisible();
          await expect(gap).toHaveCount(0);
          break;
        case "partial":
          await expect(partial).toContainText("Synthetic outgoing partial");
          await page.getByRole("slider", { name: "Display delay" }).fill("5000");
          await expect(page.getByTestId("delay-value")).toHaveText("5000 ms");
          await expect(partial).toContainText("Synthetic outgoing partial");
          break;
        case "gap":
          await expect(gap).toBeVisible();
          await expect(partial).toHaveCount(0);
          await expect(rows).toHaveCount(0);
          await expect(page.getByTestId("delay-value")).toHaveText("0 ms");
          break;
        case "final":
          await expect(rows).toHaveCount(1);
          await expect(rows.first()).toHaveText("Synthetic successor final");
          await expect(partial).toHaveCount(0);
          await expect(gap).toBeVisible();
          await gap.getByRole("button", { name: "Dismiss" }).click();
          await expect(gap).toHaveCount(0);
          break;
        default:
          throw new Error("Unknown test stage");
      }
      await expect(status).toContainText("Connected");
      checkConnection();
    }));
    process.stdout.write(stage + "\n");
  }
} finally {
  await browser.close();
}
