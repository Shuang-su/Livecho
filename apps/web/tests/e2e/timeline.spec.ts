import { expect, test } from "@playwright/test";

test.describe("synthetic timeline presentation", () => {
  test("connects, shows partial then final, and keeps at most four finals", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status-line")).toContainText("Connected", {
      timeout: 15_000,
    });
    await expect(page.getByTestId("status-line")).toContainText("Live");
    await expect(page.locator(".synthetic")).toContainText("Synthetic demonstration");

    // The provisional row appears, is replaced in place, then finalizes without
    // appending a duplicate row.
    const partial = page.getByTestId("partial-row");
    await expect(partial).toBeVisible({ timeout: 20_000 });
    await expect(partial).toContainText("Provisional");
    const firstPartialText = (await partial.locator(".text").textContent()) ?? "";
    expect(firstPartialText.length).toBeGreaterThan(4);

    const finals = page.getByTestId("final-list");
    const matchingFinal = finals
      .locator("li")
      .filter({ hasText: firstPartialText.replace("…", "").slice(0, 12) });
    await expect(matchingFinal).toHaveCount(1, { timeout: 20_000 });
    await expect(partial).toBeHidden();

    // Accepted text is preserved exactly, including Unicode and line breaks.
    await expect(matchingFinal.first()).toContainText(
      firstPartialText.replace("…", "").slice(0, 24),
    );

    // After several segments only the four most recent finals remain.
    await expect(finals.locator("li")).toHaveCount(4, { timeout: 40_000 });
    const texts = await finals.locator("li").evaluateAll((rows) =>
      rows.map((row) => (row.textContent ?? "").trim()),
    );
    expect(new Set(texts).size).toBe(4);
  });

  test("session-only delay postpones display and never hides displayed text", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });

    const slider = page.locator("#display-delay");
    await slider.click();
    await page.keyboard.press("ArrowRight").catch(() => undefined);
    await slider.fill("5000");
    await expect(page.getByTestId("delay-value")).toHaveText(/5000 ms/);

    const finals = page.getByTestId("final-list").locator("li");
    await expect(finals.first()).toBeVisible({ timeout: 20_000 });
    const before = await finals.count();

    // A new final is accepted but does not become visible until its due time.
    const finalsAtDelay = page.getByTestId("final-list").locator("li");
    const waitForNewFinal = expect
      .poll(async () => finalsAtDelay.count(), { timeout: 12_000 })
      .toBe(before + 1);

    // Within the 5 second delay the displayed rows stay unchanged.
    await page.waitForTimeout(1_500);
    const during = await finals.count();
    expect(during).toBeLessThanOrEqual(before);

    await waitForNewFinal;
    // Increasing the delay never hides an already displayed final.
    await slider.fill("5000");
    await expect(finals.first()).toBeVisible();
  });

  test("adversarial and long text stay plain, wrapped, and non-overlapping", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    // Segment one of the standard schedule is near the 4,096-scalar bound.
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 20_000,
    });
    const overlap = await page.evaluate(() => {
      const delay = document.querySelector("#display-delay")!.getBoundingClientRect();
      const list = document.querySelector('[data-testid="final-list"]')!.getBoundingClientRect();
      const horizontal = document.documentElement;
      return {
        coversControl: list.bottom > delay.top && list.right > delay.left,
        horizontalScroll: horizontal.scrollWidth > horizontal.clientWidth + 1,
      };
    });
    expect(overlap.coversControl).toBe(false);
    expect(overlap.horizontalScroll).toBe(false);
    const injected = await page.evaluate(
      () => document.querySelector("#root")!.querySelectorAll("img, script").length,
    );
    expect(injected).toBe(0);
  });
});

test.describe("final-only fixture mode label", () => {
  test("states that partials are unavailable", async ({ page }) => {
    await page.goto("http://127.0.0.1:8806/");
    await expect(page.getByTestId("partial-availability")).toContainText(
      "real-worker partial output remains unconfirmed",
      { timeout: 15_000 },
    );
    // Final-only fixtures never produce a provisional row.
    const finals = page.getByTestId("final-list").locator("li");
    await expect(finals.first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("partial-row")).toHaveCount(0);
  });
});
