import { expect, test } from "@playwright/test";

test.describe("python-backed shell storage discipline", () => {
  test("offline reload never restores timeline text from storage or cache", async ({
    page,
    context,
  }) => {
    await page.goto("http://127.0.0.1:8818/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    await expect(page.getByTestId("final-list").locator("li").first()).toBeVisible({
      timeout: 35_000,
    });
    const visible = (await page.getByTestId("final-list").locator("li").first().textContent()) ?? "";
    expect(visible.length).toBeGreaterThan(8);

    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" });
    // Shell may still load from SW allowlist; timeline text must not reappear
    // from storage without a live socket.
    await page.waitForTimeout(2_000);
    const body = await page.locator("body").innerText();
    expect(body).not.toContain(visible.slice(0, Math.min(40, visible.length)));
    const storageKeys = await page.evaluate(() => Object.keys(localStorage));
    expect(storageKeys.filter((key) => /caption|transcript|timeline|cursor/i.test(key))).toEqual(
      [],
    );
  });
});
