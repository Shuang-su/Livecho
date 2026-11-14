import { expect, test } from "@playwright/test";

/**
 * Offline shell-only caching and storage safety. The service worker may cache
 * only the static application shell; captions, events, live API responses, and
 * cursors must never reach the Service Worker cache, IndexedDB, localStorage,
 * or any other offline content storage.
 */
test.describe("PWA offline storage safety", () => {
  test("offline shows the shell only, with no timeline data anywhere", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await expect(
      page.getByTestId("final-list").locator("li").first(),
    ).toBeVisible({ timeout: 30_000 });
    const seenText = await page
      .getByTestId("final-list")
      .locator("li")
      .first()
      .textContent();

    // Wait for the service worker to control the page and precache the shell.
    await expect
      .poll(
        async () =>
          page.evaluate(async () => {
            const registration = await navigator.serviceWorker.getRegistration();
            return registration?.active?.state ?? "none";
          }),
        { timeout: 20_000 },
      )
      .toBe("activated");

    // Only allowlisted shell URLs exist in the cache.
    const cacheAudit = await page.evaluate(async () => {
      const names = await caches.keys();
      const entries: Record<string, string[]> = {};
      for (const name of names) {
        const cache = await caches.open(name);
        entries[name] = (await (cache as Cache).keys()).map((request) =>
          new URL(request.url).pathname,
        );
      }
      return entries;
    });
    const allPaths = Object.values(cacheAudit).flat();
    expect(allPaths.length).toBeGreaterThan(3);
    for (const path of allPaths) {
      expect(path.startsWith("/api/")).toBe(false);
    }
    expect(Object.keys(cacheAudit).every((name) => name.startsWith("livecho-shell-"))).toBe(
      true,
    );

    // API responses are never cacheable content (checked while online).
    const apiHeader = await page.evaluate(async () => {
      const response = await fetch("/api/viewer/absent", { cache: "no-store" });
      return response.headers.get("cache-control");
    });
    expect(apiHeader).toBe("no-store");

    // Going offline immediately clears text and labels the connection.
    await page.context().setOffline(true);
    await expect(page.getByTestId("offline-notice")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
    await expect(page.getByTestId("partial-row")).toHaveCount(0);

    // An offline reload serves the cached shell with no previous timeline text.
    await page.reload();
    await expect(page.getByTestId("offline-notice")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("status-line")).toContainText("Offline");
    const body = (await page.evaluate(() => document.body.textContent)) ?? "";
    expect(body).not.toContain("layout checks");
    if (seenText !== null && seenText.trim().length > 8) {
      expect(body).not.toContain(seenText.trim().slice(0, 12));
    }

    // No browser storage contains timeline data or a cursor.
    const storage = await page.evaluate(async () => {
      const databases = await indexedDB.databases();
      return {
        localStorage: Object.keys(window.localStorage),
        sessionStorage: Object.keys(window.sessionStorage),
        indexedDB: databases.map((entry) => entry.name ?? ""),
      };
    });
    expect(storage.localStorage).toEqual([]);
    expect(storage.sessionStorage).toEqual([]);
    expect(storage.indexedDB).toEqual([]);

    // Coming back online reconnects and resumes showing new text.
    await page.context().setOffline(false);
    await expect(page.getByTestId("status-line")).toContainText("Connected", {
      timeout: 20_000,
    });
  });
});
