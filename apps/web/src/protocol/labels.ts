import type { SessionStatus } from "./domain";

export type ConnectionState = "connecting" | "connected" | "reconnecting" | "offline" | "incompatible";

export const CONNECTION_LABELS: Readonly<Record<ConnectionState, string>> = {
  connecting: "Connecting",
  connected: "Connected",
  reconnecting: "Reconnecting",
  offline: "Offline",
  incompatible: "Incompatible",
};

export const STATUS_LABELS: Readonly<Record<SessionStatus, string>> = {
  starting: "Waiting / starting",
  live: "Live",
  stopping: "Stopping",
  stopped: "Stopped",
  failed: "Failed",
};

/**
 * Fixed public reason mapping accepted with the #9 contract. Unknown safe
 * reason codes render a generic status label, never arbitrary server text.
 */
const REASON_LABELS: Readonly<Record<string, string>> = {
  no_compatible_worker: "No compatible worker",
  ingest_disabled: "Ingest disabled",
  policy_disable: "Disabled by policy",
  session_deleted: "Session deleted",
  worker_failed: "Worker failure",
  source_failed: "Source failure",
  protocol_failed: "Protocol failure",
};

export function reasonLabel(reasonCode: string | null): string | null {
  if (reasonCode === null) return null;
  return REASON_LABELS[reasonCode] ?? "Status changed";
}

export const GAP_NOTICE = "Subtitle gap; continuing from the current position";
export const OVERFLOW_GAP_NOTICE =
  "Subtitle gap: too much accepted text arrived at once, so the view was cleared";
export const UNDISPLAYED_NOTICE = "Some subtitles were not displayed";
export const OFFLINE_NOTICE = "Offline; subtitles unavailable";
export const UNAVAILABLE_ROOM_NOTICE = "Room not available";
export const SYNTHETIC_LABEL =
  "Synthetic demonstration: fixture timeline text, not recognized speech";
export const DELAY_DISCLAIMER =
  "Display delay only postpones when accepted text becomes visible. It cannot show text before it exists, does not observe an external player's clock, and does not guarantee synchronization.";
export const PARTIAL_LABEL = "Provisional";
export const FINAL_ONLY_PARTIAL_LABEL = "Final subtitles only; partial unavailable";
export const FIXTURE_PARTIAL_LABEL =
  "Fixture partial subtitles for this demonstration; real-worker partial output remains unconfirmed";
export const UNKNOWN_PARTIAL_LABEL = "Partial availability unknown";
export const RETRY_EXHAUSTED_LABEL =
  "Could not reconnect automatically. Retry reconnects to the same room only; it never starts a room.";
