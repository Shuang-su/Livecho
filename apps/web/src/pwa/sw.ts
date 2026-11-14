/**
 * Livecho shell-only service worker.
 *
 * `vite.config.ts` replaces the two placeholders below at build time with the
 * exact allowlist of static shell files emitted into `dist/` and a shell
 * version digest. Only those same-origin URLs are ever cached: API responses,
 * WebSocket traffic, and unknown URLs never enter the cache, so no captions,
 * events, live data, or sensitive content is stored offline. There is no
 * background sync, no push, and no storage of timeline data or cursors.
 */

const SHELL_ALLOWLIST: readonly string[] = JSON.parse("__LIVECHO_SHELL_ALLOWLIST__");
const SHELL_VERSION: string = "__LIVECHO_SHELL_VERSION__";
const CACHE_NAME = `livecho-shell-${SHELL_VERSION}`;
const NAVIGATION_SHELL = "/index.html";

/**
 * Minimal service-worker global surface and event types; this keeps the
 * worker self-contained without depending on lib.webworker.
 */
interface WorkerEvent {
  waitUntil(promise: Promise<unknown>): void;
}

interface WorkerFetchRequest {
  request: Request;
  respondWith(response: Promise<Response>): void;
}

interface WorkerScope {
  location: { origin: string };
  skipWaiting(): Promise<void>;
  clients: { claim(): Promise<void> };
  addEventListener(type: "install" | "activate", listener: (event: WorkerEvent) => void): void;
  addEventListener(type: "fetch", listener: (event: WorkerFetchRequest) => void): void;
  caches: {
    open(name: string): Promise<Cache>;
    keys(): Promise<string[]>;
    delete(name: string): Promise<boolean>;
    match(request: RequestInfo): Promise<Response | undefined>;
  };
  fetch(input: RequestInfo): Promise<Response>;
}

interface Cache {
  addAll(urls: readonly string[]): Promise<void>;
  put(request: RequestInfo, response: Response): Promise<void>;
  match(request: RequestInfo): Promise<Response | undefined>;
}

const worker = self as unknown as WorkerScope;

worker.addEventListener("install", (event: WorkerEvent) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await cache.addAll(SHELL_ALLOWLIST);
    })(),
  );
  void worker.skipWaiting();
});

worker.addEventListener("activate", (event: WorkerEvent) => {
  event.waitUntil(
    (async () => {
      // Remove obsolete Livecho shell caches only; other caches are untouched
      // and no data cache exists to clear.
      for (const name of await caches.keys()) {
        if (name.startsWith("livecho-shell-") && name !== CACHE_NAME) {
          await caches.delete(name);
        }
      }
      await worker.clients.claim();
    })(),
  );
});

worker.addEventListener("fetch", (event: WorkerFetchRequest) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== worker.location.origin) return;
  if (url.pathname === "/api/viewer/ws" || url.pathname.startsWith("/api/")) {
    // Live API surfaces are never served from or written to the cache.
    return;
  }
  if (request.mode === "navigate") {
    // Network-first navigations with an offline fallback to the cached shell;
    // the app then renders its offline state without old timeline data.
    event.respondWith(
      (async () => {
        try {
          return await worker.fetch(request);
        } catch {
          const cache = await caches.open(CACHE_NAME);
          const shell = await cache.match(NAVIGATION_SHELL);
          if (shell !== undefined) return shell;
          throw new Error("offline without a cached shell");
        }
      })(),
    );
    return;
  }
  if (!SHELL_ALLOWLIST.includes(url.pathname)) {
    // Unknown URLs are never cached or served by this worker.
    return;
  }
  event.respondWith(
    (async () => {
      const cached = await caches.match(request);
      if (cached !== undefined) return cached;
      const response = await worker.fetch(request);
      if (response.ok && response.type === "basic") {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
      }
      return response;
    })(),
  );
});
