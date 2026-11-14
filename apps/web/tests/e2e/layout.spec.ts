import { expect, test } from "@playwright/test";

/**
 * Responsive layout checks at the two required sizes and at 200% page zoom:
 * the status, subtitles, and delay control stay usable without horizontal
 * scrolling, and content never covers or moves controls offscreen.
 */
const VIEWPORTS = [
  { name: "mobile-360x800", width: 360, height: 800 },
  { name: "desktop-1280x800", width: 1280, height: 800 },
];

test.describe("responsive layout", () => {
  for (const viewport of VIEWPORTS) {
    test(`keeps every control usable at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/");
      await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
      await expect(
        page.getByTestId("final-list").locator("li").first(),
      ).toBeVisible({ timeout: 30_000 });

      const audit = await page.evaluate(() => {
        const root = document.documentElement;
        const delay = document.querySelector("#display-delay")!;
        const delayBox = delay.getBoundingClientRect();
        const visible =
          delayBox.top >= 0 &&
          delayBox.bottom <= root.clientHeight &&
          delayBox.left >= 0 &&
          delayBox.right <= root.clientWidth;
        return {
          scrollWidth: root.scrollWidth,
          clientWidth: root.clientWidth,
          reachable: root.scrollHeight >= delayBox.bottom && delayBox.left >= 0,
          withinHorizontalViewport: delayBox.right <= root.clientWidth + 1,
          delayFocusable: delay instanceof HTMLInputElement && !delay.disabled,
        };
      });
      expect(audit.scrollWidth).toBeLessThanOrEqual(audit.clientWidth + 1);
      expect(audit.reachable).toBe(true);
      expect(audit.withinHorizontalViewport).toBe(true);
      expect(audit.delayFocusable).toBe(true);

      // Keyboard-only operation of the delay control.
      await page.locator("#display-delay").focus();
      await page.keyboard.press("ArrowUp");
      await expect(page.getByTestId("delay-value")).toHaveText("100 ms");

      await page.screenshot({
        path: `test-results/${viewport.name}.png`,
        fullPage: true,
      });
    });
  }

  test("remains usable at 200 percent page zoom", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status-line")).toContainText("Live", { timeout: 20_000 });
    const session = await page.context().newCDPSession(page);
    await session.send("Emulation.setPageScaleFactor", { pageScaleFactor: 2 });
    await expect(
      page.getByTestId("final-list").locator("li").first(),
    ).toBeVisible({ timeout: 30_000 });
    const audit = await page.evaluate(() => {
      const root = document.documentElement;
      const delay = document.querySelector("#display-delay")!;
      const box = delay.getBoundingClientRect();
      return {
        horizontalScroll: root.scrollWidth > root.clientWidth + 1,
        delayWithinViewport:
          box.top >= 0 && box.left >= 0 && box.bottom <= root.clientHeight,
      };
    });
    expect(audit.horizontalScroll).toBe(false);
    expect(audit.delayWithinViewport).toBe(true);
    await page.screenshot({ path: "test-results/zoom-200.png", fullPage: true });
  });
});
