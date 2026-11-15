import { expect, test } from "@playwright/test";

test.describe("stop, disable, and delete visibility priority", () => {
  test("an operator stop hides all text ahead of a maximum delay", async ({ page }) => {
    await page.goto("http://127.0.0.1:8802/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await page.locator("#display-delay").fill("5000");
    await expect(page.getByTestId("delay-value")).toHaveText(/5000 ms/);
    await expect(
      page.getByTestId("final-list").locator("li").first(),
    ).toBeVisible({ timeout: 30_000 });

    // The fixture disables ingest at segment 3: text clears immediately.
    await expect(page.getByTestId("status-line")).toContainText("Stopped", { timeout: 30_000 });
    await expect(page.getByTestId("status-line")).toContainText("Ingest disabled");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
    await expect(page.getByTestId("partial-row")).toHaveCount(0);
    await expect(page.getByTestId("empty-subtitles")).toBeVisible();
    // Nothing reappears after the delayed due time passes.
    await page.waitForTimeout(6_000);
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });

  test("session deletion hides text with its reason", async ({ page }) => {
    await page.goto("http://127.0.0.1:8803/");
    await expect(page.getByTestId("status-line")).toContainText("Session deleted", {
      timeout: 40_000,
    });
    await expect(page.getByTestId("status-line")).toContainText("Stopped");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });

  test("a fixture protocol failure renders the safe fixed label", async ({ page }) => {
    await page.goto("http://127.0.0.1:8804/");
    await expect(page.getByTestId("status-line")).toContainText("Failed", { timeout: 40_000 });
    await expect(page.getByTestId("status-line")).toContainText("Protocol failure");
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
  });
});

test.describe("disconnect and resync", () => {
  test("a refused cursor shows an explicit gap and continues from the current position", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:8805/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await expect(
      page.getByTestId("final-list").locator("li").first(),
    ).toBeVisible({ timeout: 30_000 });

    // The fixture closes every viewer after segment 2 and refuses resume.
    await expect(page.getByTestId("status-line")).toContainText("Reconnecting", {
      timeout: 30_000,
    });
    await expect(page.getByTestId("final-list").locator("li")).toHaveCount(0);
    await expect(
      page.getByTestId("gap-notice").or(page.getByTestId("undisplayed-notice")).first(),
    ).toBeVisible({ timeout: 20_000 });
    const gap = page.getByTestId("gap-notice");
    await expect(gap).toContainText(
      "Subtitle gap; continuing from the current position",
    );

    // Reconnect fresh: new text resumes without claiming history was replayed.
    await expect(page.getByTestId("status-line")).toContainText("Connected", {
      timeout: 30_000,
    });
    await expect(gap).toBeVisible();

    // Dismissal only removes the notice.
    await gap.getByRole("button", { name: "Dismiss" }).click();
    await expect(gap).toHaveCount(0);
  });
});
