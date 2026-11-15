import { expect, test } from "@playwright/test";

/**
 * Same presentation assertions as the Node-double suite, but the WebSocket
 * and schedule come from Python `livecho_backend.local_vertical`.
 */
test.describe("python fixture_timeline presentation", () => {
  test("connects, shows partial then final, and keeps at most four finals", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:8811/");
    await expect(page.getByTestId("status-line")).toContainText("Connected", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("status-line")).toContainText("Live");
    await expect(page.locator(".synthetic")).toContainText("Synthetic demonstration");

    const partial = page.getByTestId("partial-row");
    await expect(partial).toBeVisible({ timeout: 25_000 });
    await expect(partial).toContainText("Provisional");
    const firstPartialText = (await partial.locator(".text").textContent()) ?? "";
    expect(firstPartialText.length).toBeGreaterThan(4);

    const finals = page.getByTestId("final-list");
    const matchingFinal = finals
      .locator("li")
      .filter({ hasText: firstPartialText.replace("…", "").slice(0, 12) });
    await expect(matchingFinal).toHaveCount(1, { timeout: 25_000 });
    await expect(partial).toBeHidden();

    await expect(finals.locator("li")).toHaveCount(4, { timeout: 50_000 });
    const texts = await finals.locator("li").evaluateAll((rows) =>
      rows.map((row) => (row.textContent ?? "").trim()),
    );
    expect(new Set(texts).size).toBe(4);
  });

  test("session-only delay postpones display without restoring offline text", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:8817/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await page.locator("#display-delay").fill("5000");
    await expect(page.getByTestId("delay-value")).toHaveText(/5000 ms/);
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 40_000,
    });
    // No transcript text in localStorage after interaction.
    const stored = await page.evaluate(() => Object.keys(localStorage));
    expect(stored.filter((key) => /caption|transcript|timeline|cursor/i.test(key))).toEqual(
      [],
    );
  });
});

test.describe("python final-only fixture mode", () => {
  test("no provisional row when partials are disabled", async ({ page }) => {
    await page.goto("http://127.0.0.1:8816/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("partial-row")).toHaveCount(0);
  });
});
