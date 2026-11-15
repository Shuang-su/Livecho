import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { setTimeout as delay } from "node:timers/promises";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { createFixtureServer } from "../../scripts/fixture-server.mjs";
import {
  CaptionSession,
  type SessionDeps,
  type SessionSnapshot,
  type WebSocketLike,
} from "../../src/protocol/session.js";

/**
 * Issue #11 fan-out stress run: twenty simulated viewers watch the same
 * synthetic fixture timeline for about 60 seconds. Eighteen drain normally,
 * one consumes once per second, and one deliberately stalls mid-run.
 *
 * Proves UI/fan-out behavior only: every client queue stays bounded, fast
 * viewers are never held behind the slow pair, and any loss of continuity
 * surfaces as a visible gap rather than silent replay. No model, audio, or
 * worker is involved, and nothing here is MLX or end-to-end latency evidence.
 */

interface PacedSocket extends WebSocketLike {
  resumeDelivery(): void;
}

function pacedSocketFactory(
  url: string,
  protocols: string[],
  rateHz: number | null,
): PacedSocket {
  const real = new WebSocket(url, protocols);
  const messageQueue: string[] = [];
  const listeners = new Map<string, Array<(event: { data?: unknown }) => void>>();
  let running = rateHz !== null;
  const pump = (): void => {
    if (!running) return;
    const batch = messageQueue.splice(0);
    for (const data of batch) {
      for (const listener of [...(listeners.get("message") ?? [])]) listener({ data });
    }
  };
  if (rateHz !== null) {
    const interval = setInterval(pump, Math.round(1000 / rateHz));
    real.addEventListener("close", () => clearInterval(interval));
  }
  real.addEventListener("open", () => {
    for (const listener of [...(listeners.get("open") ?? [])]) listener({});
  });
  real.addEventListener("close", () => {
    running = false;
    for (const listener of [...(listeners.get("close") ?? [])]) listener({});
  });
  real.addEventListener("message", (event: MessageEvent<string>) => {
    const data = event.data;
    if (typeof data === "string") {
      messageQueue.push(data);
      // A resumed stalled socket delivers immediately; paced sockets wait
      // for their interval pump.
      if (running && rateHz === null) pump();
    }
  });
  const socket: PacedSocket = {
    get readyState() {
      return real.readyState;
    },
    send(data: string) {
      real.send(data);
    },
    close() {
      real.close();
    },
    addEventListener(type: string, listener: (event: { data?: unknown }) => void) {
      const existing = listeners.get(type) ?? [];
      existing.push(listener);
      listeners.set(type, existing);
    },
    resumeDelivery() {
      running = true;
      pump();
    },
  };
  return socket;
}

const ALWAYS_ONLINE = {
  isOnline: () => true,
  onOnline: () => () => undefined,
  onOffline: () => () => undefined,
  onVisible: () => () => undefined,
};

describe("twenty-viewer fixture fan-out", () => {
  let port = 0;
  let server: ReturnType<typeof createFixtureServer> | null = null;
  const sessions: CaptionSession[] = [];
  const paced: PacedSocket[] = [];

  beforeAll(async () => {
    server = createFixtureServer({
      root: "dist",
      host: "127.0.0.1",
      port: 0,
      room: "livecho.fixture.room",
      segments: 19,
      intervalMs: 3_000,
      stopAt: -1,
      stopReason: "ingest_disabled",
      failAt: -1,
      deleteAt: -1,
      closeAt: -1,
      refuseResume: false,
      noPartials: false,
      staticOnly: false,
    });
    port = await new Promise<number>((resolve) => {
      server!.httpServer.listen(0, "127.0.0.1", () => {
        const address = server!.httpServer.address();
        resolve(typeof address === "object" && address !== null ? address.port : 0);
      });
    });
  });

  afterAll(async () => {
    for (const session of sessions) session.dispose();
    await server?.close();
  });

  it("keeps fast, slow, and stalled viewers isolated with bounded queues", async () => {
    expect(port).toBeGreaterThan(0);
    const url = `ws://127.0.0.1:${port}/api/viewer/ws`;

    for (let index = 0; index < 18; index += 1) {
      sessions.push(
        new CaptionSession({
          url,
          roomId: "livecho.fixture.room",
          clock: { now: () => performance.now() },
          environment: ALWAYS_ONLINE,
        }),
      );
    }
    // Viewer 18 consumes its socket once per second.
    sessions.push(
      new CaptionSession({
        url,
        roomId: "livecho.fixture.room",
        clock: { now: () => performance.now() },
        environment: ALWAYS_ONLINE,
        webSocketFactory: (target, protocols) => {
          const socket = pacedSocketFactory(target, protocols, 1);
          paced.push(socket);
          return socket;
        },
      }),
    );
    // Viewer 19 stalls for 30 seconds, then resumes with a 5 second delay.
    const stalledRef: { socket: PacedSocket | null } = { socket: null };
    sessions.push(
      new CaptionSession({
        url,
        roomId: "livecho.fixture.room",
        clock: { now: () => performance.now() },
        environment: ALWAYS_ONLINE,
        webSocketFactory: (target: string, protocols: string[]) => {
          const socket = pacedSocketFactory(target, protocols, null);
          stalledRef.socket = socket;
          return socket;
        },
      }),
    );
    await delay(200);
    sessions[19]!.setDelay(5_000);
    await delay(28_000);
    stalledRef.socket?.resumeDelivery();

    // Wait for the schedule to complete (19 segments at 3s plus stop events).
    await delay(34_000);

    const snapshots = sessions.map((session) => session.getSnapshot());
    const fast = snapshots.slice(0, 18);
    const slow = snapshots[18]!;
    const stalledViewer = snapshots[19]!;

    console.log(
      "per-client:",
      JSON.stringify(
        snapshots.map((snapshot, index) => ({
          index,
          connection: snapshot.connection,
          status: snapshot.sessionStatus,
          reason: snapshot.statusReason,
          received: snapshot.metrics.receivedEvents,
          rejected: snapshot.metrics.rejectedFrames,
          duplicates: snapshot.metrics.duplicates,
          resyncs: snapshot.metrics.resyncs,
          applied: snapshot.metrics.appliedMutations,
        })),
      ),
    );

    const summary = {
      fast: {
        appliedRange: [
          Math.min(...fast.map((s) => s.metrics.appliedMutations)),
          Math.max(...fast.map((s) => s.metrics.appliedMutations)),
        ],
        resyncsTotal: fast.reduce((sum, s) => sum + s.metrics.resyncs, 0),
        renderLagMaxMs: Math.max(...fast.map((s) => s.metrics.renderLagMaxMs)),
        queuePeakMax: Math.max(...fast.map((s) => s.metrics.queuePeak)),
        queueBytesPeakMax: Math.max(...fast.map((s) => s.metrics.queueBytesPeak)),
      },
      slowOncePerSecond: summarize(slow),
      stalledViewer: summarize(stalledViewer),
    };
    console.log("stress summary:", JSON.stringify(summary, null, 2));
    const resultsDirectory = join(import.meta.dirname, "../../test-results");
    await mkdir(resultsDirectory, { recursive: true });
    await writeFile(
      join(resultsDirectory, "stress-summary.json"),
      `${JSON.stringify(summary, null, 2)}\n`,
      "utf8",
    );

    // Every client queue stayed bounded.
    for (const snapshot of snapshots) {
      expect(snapshot.metrics.queuePeak).toBeLessThanOrEqual(128);
      expect(snapshot.metrics.queueBytesPeak).toBeLessThanOrEqual(262_144);
      expect(snapshot.connection).not.toBe("incompatible");
    }

    // Fast viewers never waited for the slow pair: they all applied the same
    // transcript mutations, none lost continuity, and render lag stayed small.
    expect(summary.fast.resyncsTotal).toBe(0);
    const applied = fast.map((s) => s.metrics.appliedMutations);
    expect(new Set(applied).size).toBe(1);
    expect(applied[0]).toBeGreaterThan(30);
    expect(summary.fast.renderLagMaxMs).toBeLessThan(2_000);
    for (const snapshot of fast) {
      expectTerminalState(snapshot);
    }

    // The slow and stalled viewers ended on the terminal status with bounded
    // state; any resync they experienced is visible as a gap notice.
    expect(stalledViewer.metrics.appliedMutations).toBeGreaterThan(0);
    if (slow.metrics.resyncs > 0 || stalledViewer.metrics.resyncs > 0) {
      expect(slow.notices.gap || stalledViewer.notices.gap).toBe(true);
    }
    expectTerminalState(slow);
    expectTerminalState(stalledViewer);
  }, 120_000);
});

function summarize(snapshot: SessionSnapshot) {
  return {
    resyncs: snapshot.metrics.resyncs,
    applied: snapshot.metrics.appliedMutations,
    queuePeak: snapshot.metrics.queuePeak,
    queueBytesPeak: snapshot.metrics.queueBytesPeak,
    gapVisible: snapshot.notices.gap,
    overflowVisible: snapshot.notices.overflow,
  };
}

function expectTerminalState(snapshot: SessionSnapshot): void {
  expect(snapshot.sessionStatus).toBe("stopped");
  expect(snapshot.finals).toHaveLength(0);
  expect(snapshot.partial).toBeNull();
}
