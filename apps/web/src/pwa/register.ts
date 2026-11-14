/**
 * Register the shell-only service worker in production builds.
 *
 * In development (`pnpm dev`) no service worker is registered so the Vite dev
 * server never caches anything.
 */
export function registerServiceWorker(): void {
  if (!import.meta.env.PROD) return;
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => {
      // Offline caching is an enhancement only; the page stays usable.
    });
  });
}
