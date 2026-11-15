import { expect, test } from "@playwright/test";

test.describe("python stop, disable, and delete visibility priority", () => {
  test("an operator stop hides all text ahead of a maximum delay", async ({ page }) => {
    await page.goto("http://127.0.0.1:8812/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await page.locator("#display-delay").fill("5000");
    await expect(page.getByTestId("delay-value")).toHaveText(/5000 ms/);
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 35_000,
    });

    await expect(page.getByTestId("status-line")).toContainText("Stopped", { timeout: 40_000 });
    await expect(page.getByTestId("status-line")).toContainText("Ingest disabled");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
    await expect(page.getByTestId("partial-row")).toHaveCount(0);
    await expect(page.getByTestId("empty-subtitles")).toBeVisible();
    await page.waitForTimeout(6_000);
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });

  test("session deletion hides text with its reason", async ({ page }) => {
    await page.goto("http://127.0.0.1:8813/");
    await expect(page.getByTestId("status-line")).toContainText("Session deleted", {
      timeout: 45_000,
    });
    await expect(page.getByTestId("status-line")).toContainText("Stopped");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });

  test("a fixture protocol failure renders the safe fixed label", async ({ page }) => {
    await page.goto("http://127.0.0.1:8814/");
    await expect(page.getByTestId("status-line")).toContainText("Failed", { timeout: 45_000 });
    await expect(page.getByTestId("status-line")).toContainText("Protocol failure");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });
});

test.describe("python disconnect and resync", () => {
  test("a refused cursor shows an explicit gap and continues from the current position", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:8815/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 35_000,
    });

    await expect(page.getByTestId("status-line")).toContainText("Reconnecting", {
      timeout: 40_000,
    });
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
    await expect(
      page.getByTestId("gap-notice").or(page.getByTestId("undisplayed-notice")).first(),
    ).toBeVisible({ timeout: 25_000 });
    const gap = page.getByTestId("gap-notice");
    await expect(gap).toContainText("Subtitle gap; continuing from the current position");

    await expect(page.getByTestId("status-line")).toContainText("Connected", {
      timeout: 40_000,
    });
    await expect(gap).toBeVisible();
    await gap.getByRole("button", { name: "Dismiss" }).click();
    await expect(gap).toHaveCount(0);
  });
});
