#!/usr/bin/env node
/**
 * Local `fixture_timeline` fixture server for the Issue #11 caption page.
 *
 * This is a test/demo double for the accepted Issue #9 contract — NOT the
 * production backend. It serves the built static shell and mounts the exact
 * same-origin `GET /api/viewer/ws` viewer handshake with:
 *
 * - `livecho.viewer.v1` subprotocol negotiation and a `ViewerSubscribeV1`
 *   handshake (fresh or cursor resume);
 * - a shared synthetic transcript/status timeline with stable event IDs and
 *   at most one mutable partial at a time (final within 1,000 ms, then at
 *   least 2,000 ms before the next mutable object);
 * - fresh subscriptions refused with `resync_required` while a partial is
 *   open, and served a newly sequenced current status otherwise;
 * - cursor resume only when the retained 10-second domain matches the
 *   timeline's exact next position;
 * - bounded per-viewer fan-out (32 unsent messages, 262,144 unsent bytes,
 *   500 ms send deadline) that removes a slow viewer without blocking others;
 * - terminal statuses sent only at an exact-next clear boundary (otherwise
 *   the viewer is closed without flushing).
 *
 * Every outbound frame is validated through the shared
 * `@livecho/protocol` Node entry, so fixture output cannot drift from the
 * generated schemas. Requires `packages/protocol` to be built (`pnpm build`).
 */
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { pathToFileURL } from "node:url";
import { WebSocketServer } from "ws";
import { randomUUID } from "node:crypto";
import {
  PROTOCOL_MINOR,
  VIEWER_PROTOCOL,
  canonicalJson,
  strictJsonParse,
  validateModel,
} from "@livecho/protocol";

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
};

const MAX_VIEWERS = 20;
const DOMAIN_RETENTION_MS = 10_000;
const PER_VIEWER_UNSENT_MESSAGES = 32;
const PER_VIEWER_UNSENT_BYTES = 262_144;
const SEND_DEADLINE_MS = 500;
const TERMINAL_SESSION_STATUSES = new Set(["stopping", "stopped", "failed"]);

function parseArguments(argv) {
  const options = {
    root: "dist",
    host: "127.0.0.1",
    port: 8787,
    room: "livecho.fixture.room",
    segments: 12,
    intervalMs: 3_000,
    noPartials: false,
    stopAt: -1,
    stopReason: "ingest_disabled",
    failAt: -1,
    deleteAt: -1,
    closeAt: -1,
    refuseResume: false,
    staticOnly: false,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const argument = argv[index];
    const next = () => argv[(index += 1)];
    switch (argument) {
      case "--root": options.root = next(); break;
      case "--host": options.host = next(); break;
      case "--port": options.port = Number(next()); break;
      case "--room": options.room = next(); break;
      case "--segments": options.segments = Number(next()); break;
      case "--interval": options.intervalMs = Number(next()); break;
      case "--no-partials": options.noPartials = true; break;
      case "--stop-at": options.stopAt = Number(next()); break;
      case "--stop-reason": options.stopReason = next(); break;
      case "--fail-at": options.failAt = Number(next()); break;
      case "--delete-at": options.deleteAt = Number(next()); break;
      case "--close-at": options.closeAt = Number(next()); break;
      case "--refuse-resume": options.refuseResume = true; break;
      case "--static-only": options.staticOnly = true; break;
      default:
        throw new Error(`unknown option: ${argument}`);
    }
  }
  return options;
}

function nowStamp() {
  return new Date().toISOString();
}

function assertValidFrame(model, wire) {
  const code = validateModel(model, wire);
  if (code !== "accepted") {
    throw new Error(`fixture frame failed shared validation (${model}): ${code}`);
  }
}

function envelope(type, extra) {
  const message = {
    protocol: VIEWER_PROTOCOL,
    protocol_minor: PROTOCOL_MINOR,
    message_id: randomUUID(),
    sent_at: nowStamp(),
    type,
    ...extra,
  };
  assertValidFrame(type === "viewer.ready" ? "ViewerReadyV1" : type === "viewer.subscribe" ? "ViewerSubscribeV1" : type === "protocol.error" ? "ProtocolErrorV1" : "ProtocolAckV1", message);
  return message;
}

/** Shared synthetic timeline: one session, epoch 1, monotonically increasing seq. */
class FixtureTimeline {
  constructor(options) {
    this.sessionId = randomUUID();
    this.roomId = options.room;
    this.epoch = "1";
    this.nextSeq = 1n;
    this.status = "stopped";
    this.reasonCode = null;
    this.mutableOpen = false;
    this.subscribers = new Set();
    this.retainedDomains = new Map(); // domain key -> {nextSeq, expiresAt}
    this.options = options;
  }

  allocate() {
    const seq = this.nextSeq;
    this.nextSeq += 1n;
    return seq;
  }

  key(sessionId, epoch, nextSeq) {
    return `${sessionId}|${epoch}|${nextSeq}`;
  }

  retainDomain(sessionId, epoch, nextSeq) {
    if (this.retainedDomains.size >= MAX_VIEWERS) {
      const oldest = this.retainedDomains.keys().next();
      if (!oldest.done) this.retainedDomains.delete(oldest.value);
    }
    this.retainedDomains.set(this.key(sessionId, epoch, nextSeq), {
      nextSeq,
      expiresAt: Date.now() + DOMAIN_RETENTION_MS,
    });
  }

  canResume(cursor) {
    if (this.options.refuseResume) return false;
    if (cursor.session_id !== this.sessionId || cursor.epoch !== this.epoch) return false;
    if (cursor.next_seq !== this.nextSeq.toString()) return false;
    const retained = this.retainedDomains.get(this.key(cursor.session_id, cursor.epoch, cursor.next_seq));
    return retained !== undefined && retained.expiresAt > Date.now();
  }

  event(seq, revision, eventId, payload, occurredAt) {
    return {
      protocol: VIEWER_PROTOCOL,
      protocol_minor: PROTOCOL_MINOR,
      message_id: randomUUID(),
      sent_at: nowStamp(),
      type: "viewer.timeline_event",
      event_id: eventId,
      session_id: this.sessionId,
      room_id: this.roomId,
      epoch: this.epoch,
      seq: seq.toString(),
      revision: revision.toString(),
      occurred_at: occurredAt,
      payload,
    };
  }

  publish(frame) {
    assertValidFrame("TimelineEventV1", frame);
    const payload = frame.payload;
    if ("status" in payload) {
      this.status = payload.status;
      this.reasonCode = payload.reason_code ?? null;
    }
    this.emitToSubscribers(frame);
  }

  emitToSubscribers(frame) {
    const isTerminal =
      "status" in frame.payload &&
      ["stopping", "stopped", "failed"].includes(frame.payload.status);
    for (const viewer of [...this.subscribers]) {
      viewer.deliver(frame, isTerminal);
    }
  }

  statusEvent(status, reasonCode = null) {
    const payload = reasonCode === null ? { status } : { status, reason_code: reasonCode };
    return this.event(this.allocate(), 1n, randomUUID(), payload, nowStamp());
  }

  transcriptEvent(seq, revision, eventId, segmentId, startMs, endMs, text, isFinal, occurredAt) {
    return this.event(
      seq,
      revision,
      eventId,
      {
        segment_id: segmentId,
        start_ms: startMs,
        end_ms: endMs,
        text,
        is_final: isFinal,
      },
      occurredAt,
    );
  }
}

/** One admitted viewer connection with bounded send ownership. */
class ViewerConnection {
  constructor(socket, timeline) {
    this.socket = socket;
    this.timeline = timeline;
    this.unsentMessages = 0;
    this.stallSince = null;
    this.nextSeq = null;
    this.open = true;
    this.receivedFrames = 0;
  }

  send(frame) {
    if (!this.open) return;
    const text = canonicalJson(frame);
    const before = this.socket.bufferedAmount;
    this.socket.send(text);
    const after = this.socket.bufferedAmount;
    if (after > 0) {
      if (this.stallSince === null) this.stallSince = Date.now();
      this.unsentMessages += before > 0 ? 1 : 0;
    }
  }

  /** Bounded delivery with the accepted terminal clear-send rule. */
  deliver(frame, isTerminal) {
    if (!this.open) return;
    const pendingBytes = this.socket.bufferedAmount;
    if (isTerminal && pendingBytes > 0) {
      // Never flush old text to reach a terminal event, and never send a
      // terminal across a discarded position: close the viewer.
      this.close();
      return;
    }
    if (pendingBytes > 0) {
      if (
        this.unsentMessages + 1 > PER_VIEWER_UNSENT_MESSAGES ||
        pendingBytes > PER_VIEWER_UNSENT_BYTES ||
        Date.now() - this.stallSince > SEND_DEADLINE_MS
      ) {
        this.close();
        return;
      }
    }
    this.send(frame);
    if (frame.type === "viewer.timeline_event") {
      this.nextSeq = BigInt(frame.seq) + 1n;
    }
  }

  enforceCaps() {
    if (!this.open) return;
    const pending = this.socket.bufferedAmount;
    if (pending === 0) {
      this.unsentMessages = 0;
      this.stallSince = null;
      return;
    }
    if (
      pending > PER_VIEWER_UNSENT_BYTES ||
      this.unsentMessages > PER_VIEWER_UNSENT_MESSAGES ||
      (this.stallSince !== null && Date.now() - this.stallSince > SEND_DEADLINE_MS)
    ) {
      this.close();
    }
  }

  close() {
    if (!this.open) return;
    this.open = false;
    this.timeline.subscribers.delete(this);
    if (this.nextSeq !== null) {
      this.timeline.retainDomain(this.timeline.sessionId, this.timeline.epoch, this.nextSeq);
    }
    this.socket.close(1000);
    // A stalled socket that cannot complete the close handshake is terminated
    // after a bounded grace period; queued bodies are already abandoned.
    setTimeout(() => this.socket.terminate(), 1_000);
  }
}

const SEGMENT_TEXTS = [
  "Welcome to the Livecho synthetic caption demonstration.",
  "This stream is a fixture timeline; it is not recognized speech.",
  "实时字幕为合成夹具，不代表真实语音识别。",
  `Long words cannot push controls offscreen: ${"interoperability".repeat(20)}`,
  "The companion page shows one provisional row and four recent final rows.",
  "You can postpone display by up to five seconds, in steps of one tenth.",
  "Disconnecting immediately clears captions so nothing looks live while offline.",
  "\u{1f5e3}\ufe0f Emojis and line breaks\nare preserved exactly.",
  "A gap notice appears after a resync; it never claims history was replayed.",
  "Stopping the session hides all text at once, ahead of any pending delay.",
  "The demonstration stores no captions on your device, online or offline.",
  "That completes the fixture schedule; the room remains available for review.",
];

function longTextSegment() {
  // Near the accepted 4,096-scalar text bound; still fits the display budget.
  const base = "Synthetic fixture text for layout checks. ";
  const text = base.repeat(Math.floor(4096 / base.length));
  return text.slice(0, 4090);
}

export function createFixtureServer(options) {
  const timeline = new FixtureTimeline(options);
  const httpServer = createServer(async (request, response) => {
    try {
      if (request.url !== undefined && request.url.startsWith("/api/")) {
        response.writeHead(404, { "Cache-Control": "no-store" });
        response.end('{"error":"not_found"}');
        return;
      }
      const url = new URL(request.url ?? "/", "http://localhost");
      let pathname = url.pathname;
      if (pathname === "/") pathname = "/index.html";
      const relative = normalize(pathname).replace(/^([/\\]|\.\.)+/, "");
      const filePath = join(options.root, relative);
      if (!filePath.startsWith(normalize(options.root))) {
        response.writeHead(404, { "Cache-Control": "no-store" });
        response.end();
        return;
      }
      const info = await stat(filePath).catch(() => null);
      if (info === null || !info.isFile()) {
        response.writeHead(404, { "Cache-Control": "no-store" });
        response.end();
        return;
      }
      const body = await readFile(filePath);
      const type = CONTENT_TYPES[extname(filePath)] ?? "application/octet-stream";
      const hashed = /-[0-9a-f]{8,}\.(?:js|css|svg|png)$/.test(filePath);
      response.writeHead(200, {
        "Content-Type": type,
        "Cache-Control": hashed ? "public, max-age=31536000, immutable" : "no-cache",
      });
      response.end(body);
    } catch {
      response.writeHead(500, { "Cache-Control": "no-store" });
      response.end();
    }
  });

  let webSocketServer = null;
  const timers = [];

  if (!options.staticOnly) {
    webSocketServer = new WebSocketServer({ noServer: true });

    httpServer.on("upgrade", (request, socket, head) => {
      const { pathname } = new URL(request.url ?? "/", "http://localhost");
      const protocols = (request.headers["sec-websocket-protocol"] ?? "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      if (pathname !== "/api/viewer/ws" || !protocols.includes(VIEWER_PROTOCOL)) {
        socket.write("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n");
        socket.destroy();
        return;
      }
      webSocketServer.handleUpgrade(request, socket, head, (ws) => {
        webSocketServer.emit("connection", ws, request);
      });
    });

    webSocketServer.on("connection", (ws) => {
      if (timeline.subscribers.size >= MAX_VIEWERS) {
        ws.close(1013);
        return;
      }
      const viewer = new ViewerConnection(ws, timeline);
      ws.on("message", (data, isBinary) => {
        if (isBinary) return;
        handleSubscribe(viewer, data.toString());
      });
      ws.on("close", () => {
        viewer.open = false;
        timeline.subscribers.delete(viewer);
        if (viewer.nextSeq !== null) {
          timeline.retainDomain(timeline.sessionId, timeline.epoch, viewer.nextSeq);
        }
      });
      ws.on("error", () => {
        viewer.close();
      });
    });

    function handleSubscribe(viewer, text) {
      const parsed = strictJsonParse(text);
      if (parsed.code !== "accepted") {
        protocolError(viewer, "malformed_json", "Rejected control input", false);
        return;
      }
      const value = parsed.value;
      if (validateModel("ViewerSubscribeV1", value) !== "accepted") {
        protocolError(viewer, "schema_invalid", "Rejected subscribe", false);
        return;
      }
      if (value.room_id !== options.room) {
        protocolError(viewer, "binding_mismatch", "Unknown room", false);
        return;
      }
      if (value.cursor !== undefined && value.cursor !== null) {
        if (timeline.canResume(value.cursor)) {
          admit(viewer, true, value.cursor.next_seq);
        } else {
          protocolError(viewer, "resync_required", "Cursor cannot be resumed", true);
        }
        return;
      }
      if (timeline.mutableOpen) {
        protocolError(viewer, "resync_required", "Retry after the open segment finalizes", true);
        return;
      }
      admit(viewer, false, null);
    }

    function admit(viewer, resumed, nextSeq) {
      if (
        !resumed &&
        TERMINAL_SESSION_STATUSES.has(timeline.status) &&
        timeline.subscribers.size === 0
      ) {
        // A fresh subscribe after a finished, idle demonstration starts a new
        // immutable session with a fresh session UUID and epoch 1, so every
        // E2E run observes a deterministic timeline from the beginning.
        startSession();
      }
      timeline.subscribers.add(viewer);
      let ready;
      if (resumed) {
        ready = envelope("viewer.ready", {
          cursor_resumed: true,
          session_id: timeline.sessionId,
          epoch: timeline.epoch,
          next_seq: nextSeq,
          minimum_client_version: "0.1.0",
          selected_minor: PROTOCOL_MINOR,
        });
        viewer.nextSeq = BigInt(nextSeq);
        viewer.send(ready);
        return;
      }
      const statusFrame = timeline.statusEvent(timeline.status, timeline.reasonCode);
      ready = envelope("viewer.ready", {
        cursor_resumed: false,
        session_id: timeline.sessionId,
        epoch: timeline.epoch,
        next_seq: statusFrame.seq,
        minimum_client_version: "0.1.0",
        selected_minor: PROTOCOL_MINOR,
      });
      viewer.nextSeq = BigInt(statusFrame.seq);
      viewer.send(ready);
      timeline.publish(statusFrame);
    }

    function protocolError(viewer, code, message, retryable) {
      const frame = envelope("protocol.error", { code, message, retryable });
      assertValidFrame("ProtocolErrorV1", frame);
      viewer.send(frame);
      viewer.close();
    }
  }

  function schedule() {
    if (options.staticOnly) return;
    timeline.publish(timeline.statusEvent("starting"));
    timers.push(setTimeout(() => timeline.publish(timeline.statusEvent("live")), 300));

    const total = Math.max(1, options.segments);
    const segmentStep = Math.max(2_500, options.intervalMs);
    for (let index = 0; index < total; index += 1) {
      const at = 800 + index * segmentStep;
      if (options.stopAt === index + 1) {
        timers.push(
          setTimeout(() => {
            timeline.publish(timeline.statusEvent("stopped", options.stopReason));
          }, at),
        );
        return;
      }
      if (options.deleteAt === index + 1) {
        timers.push(
          setTimeout(() => {
            timeline.publish(timeline.statusEvent("stopped", "session_deleted"));
          }, at),
        );
        return;
      }
      if (options.failAt === index + 1) {
        timers.push(
          setTimeout(() => {
            timeline.publish(timeline.statusEvent("failed", "protocol_failed"));
          }, at),
        );
        return;
      }
      const segmentId = randomUUID();
      const eventId = randomUUID();
      const occurredAt = nowStamp();
      const startMs = at;
      const endMs = at + 2_000;
      const text = index === 0 ? longTextSegment() : SEGMENT_TEXTS[index % SEGMENT_TEXTS.length];
      const publishPartial = !options.noPartials;
      // Sequence positions are allocated at publish time so the shared
      // timeline position always matches fan-out order; each revision of a
      // mutable object consumes the next position per the v1 contract.
      if (publishPartial) {
        const partialText = `${text.slice(0, Math.ceil(text.length / 2))}…`;
        timers.push(
          setTimeout(() => {
            timeline.mutableOpen = true;
            timeline.publish(
              timeline.transcriptEvent(
                timeline.allocate(),
                1n,
                eventId,
                segmentId,
                startMs,
                endMs,
                partialText,
                false,
                occurredAt,
              ),
            );
          }, at),
        );
      }
      timers.push(
        setTimeout(() => {
          timeline.mutableOpen = false;
          timeline.publish(
            timeline.transcriptEvent(
              timeline.allocate(),
              publishPartial ? 2n : 1n,
              eventId,
              segmentId,
              startMs,
              endMs,
              text,
              true,
              occurredAt,
            ),
          );
          if (options.closeAt === index + 1) {
            for (const other of [...timeline.subscribers]) {
              other.socket.close(1000);
            }
          }
        }, at + (publishPartial ? 600 : 0)),
      );
    }

    const completionAt = 800 + total * segmentStep + 1_500;
    timers.push(
      setTimeout(() => {
        timeline.publish(timeline.statusEvent("stopping"));
      }, completionAt),
    );
    timers.push(
      setTimeout(() => {
        timeline.publish(timeline.statusEvent("stopped"));
      }, completionAt + 400),
    );
  }

  const capsInterval = setInterval(() => {
    for (const viewer of timeline.subscribers) viewer.enforceCaps();
    const now = Date.now();
    for (const [key, domain] of timeline.retainedDomains) {
      if (domain.expiresAt <= now) timeline.retainedDomains.delete(key);
    }
  }, 100);
  timers.push(capsInterval);

  /**
   * Start a new immutable fixture session (fresh UUID, epoch 1, sequence 1).
   * The first fresh subscribe after a terminal, idle session triggers this so
   * every test observes the timeline from its beginning; an active session is
   * joined as-is for same-session reconnect tests.
   */
  function startSession() {
    timeline.sessionId = randomUUID();
    timeline.nextSeq = 1n;
    timeline.status = "starting";
    timeline.reasonCode = null;
    timeline.mutableOpen = false;
    timeline.retainedDomains.clear();
    schedule();
  }

  return {
    httpServer,
    timeline,
    close() {
      for (const timer of timers) clearTimeout(timer);
      clearInterval(capsInterval);
      for (const viewer of [...timeline.subscribers]) viewer.socket.terminate();
      webSocketServer?.close();
      return new Promise((resolve) => httpServer.close(() => resolve()));
    },
  };
}

export { parseArguments };

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const options = parseArguments(process.argv);
  const fixture = createFixtureServer(options);
  fixture.httpServer.listen(options.port, options.host, () => {
    process.stdout.write(
      `fixture server: http://${options.host}:${options.port} (room ${options.room})\n`,
    );
  });
}
