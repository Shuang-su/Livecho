import { useMemo } from "react";
import {
  CONNECTION_LABELS,
  DELAY_DISCLAIMER,
  GAP_NOTICE,
  OVERFLOW_GAP_NOTICE,
  PARTIAL_LABEL,
  RETRY_EXHAUSTED_LABEL,
  STATUS_LABELS,
  SYNTHETIC_LABEL,
  UNAVAILABLE_ROOM_NOTICE,
  reasonLabel,
} from "../protocol/labels";
import { CONFIGURED_ROOM_ID, PARTIAL_AVAILABILITY_LABEL, resolveRequestedRoom } from "../config";
import { CaptionSession, type SessionDeps, type SessionSnapshot } from "../protocol/session";
import { useCaptionSession, useSessionSnapshot } from "./useCaptionSession";

export function App(): React.JSX.Element {
  const selection = useMemo(
    () => resolveRequestedRoom(window.location.pathname, CONFIGURED_ROOM_ID),
    [],
  );
  if (!selection.ok) return <UnavailableRoom />;
  return <RoomView roomId={selection.roomId} />;
}

function UnavailableRoom(): React.JSX.Element {
  return (
    <main className="app">
      <header className="app-header">
        <h1>Livecho captions</h1>
        <p className="synthetic">{SYNTHETIC_LABEL}</p>
      </header>
      <p role="status" className="status-line">
        {UNAVAILABLE_ROOM_NOTICE}
      </p>
    </main>
  );
}

function roomSessionDeps(roomId: string): SessionDeps {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return {
    url: `${protocol}//${window.location.host}/api/viewer/ws`,
    roomId,
    clock: { now: () => performance.now() },
    environment: browserEnvironment(),
  };
}

function browserEnvironment(): SessionDeps["environment"] {
  return {
    isOnline: () => navigator.onLine,
    onOnline: (listener) => {
      window.addEventListener("online", listener);
      return () => window.removeEventListener("online", listener);
    },
    onOffline: (listener) => {
      window.addEventListener("offline", listener);
      return () => window.removeEventListener("offline", listener);
    },
    onVisible: (listener) => {
      document.addEventListener("visibilitychange", listener);
      return () => document.removeEventListener("visibilitychange", listener);
    },
  };
}

export function RoomView({ roomId }: { roomId: string }): React.JSX.Element {
  const deps = useMemo(() => roomSessionDeps(roomId), [roomId]);
  const session = useCaptionSession(deps);
  const snapshot = useSessionSnapshot(session);
  return <RoomPanel session={session} snapshot={snapshot} roomId={roomId} />;
}

export function RoomPanel({
  session,
  snapshot,
  roomId,
}: {
  session: CaptionSession;
  snapshot: SessionSnapshot;
  roomId: string;
}): React.JSX.Element {
  const statusLabel =
    snapshot.sessionStatus === null ? null : STATUS_LABELS[snapshot.sessionStatus];
  const reason = reasonLabel(snapshot.statusReason);
  const offline = snapshot.connection === "offline";
  return (
    <main className="app">
      <header className="app-header">
        <h1>Livecho captions</h1>
        <p className="synthetic">{SYNTHETIC_LABEL}</p>
        <p className="room">
          Room <code>{roomId}</code>
        </p>
      </header>

      <section className="status-panel" aria-label="Connection and session status">
        <p role="status" aria-live="polite" className="status-line" data-testid="status-line">
          <span className="chip" data-connection={snapshot.connection}>
            {CONNECTION_LABELS[snapshot.connection]}
          </span>
          {statusLabel !== null && (
            <span className="chip" data-session-status={snapshot.sessionStatus}>
              {statusLabel}
            </span>
          )}
          {reason !== null && <span className="reason">{reason}</span>}
        </p>
        {offline && (
          <p className="notice" data-testid="offline-notice">
            Offline; subtitles unavailable
          </p>
        )}
        {snapshot.retryOffered && (
          <p className="notice" data-testid="retry-offer">
            {RETRY_EXHAUSTED_LABEL}{" "}
            <button type="button" onClick={() => session.retry()}>
              Retry
            </button>
          </p>
        )}
      </section>

      <section className="notices" aria-label="Subtitle notices">
        {snapshot.notices.gap && (
          <p className="notice" data-testid="gap-notice">
            {GAP_NOTICE}{" "}
            <button type="button" onClick={() => session.dismissGap()}>
              Dismiss
            </button>
          </p>
        )}
        {snapshot.notices.overflow && (
          <p className="notice" data-testid="overflow-notice">
            {OVERFLOW_GAP_NOTICE}{" "}
            <button type="button" onClick={() => session.dismissOverflow()}>
              Dismiss
            </button>
          </p>
        )}
        {snapshot.notices.undisplayed && (
          <p className="notice" data-testid="undisplayed-notice">
            Some subtitles were not displayed{" "}
            <button type="button" onClick={() => session.dismissUndisplayed()}>
              Dismiss
            </button>
          </p>
        )}
      </section>

      <section className="subtitles" aria-label="Current subtitles">
        {snapshot.partial !== null && (
          // Partial updates are not announced on every revision.
          <p className="partial" data-testid="partial-row">
            <span className="tag">{PARTIAL_LABEL}</span>
            <span className="text">{snapshot.partial.text}</span>
          </p>
        )}
        <ol
          className="finals"
          aria-live="polite"
          aria-label="Recent final subtitles"
          data-testid="final-list"
        >
          {snapshot.finals.map((row) => (
            <li key={row.eventId} className="final" data-seq={row.seq.toString()}>
              <span className="text">{row.text}</span>
            </li>
          ))}
        </ol>
        {snapshot.finals.length === 0 && snapshot.partial === null && (
          <p className="empty" data-testid="empty-subtitles">
            Waiting for subtitles…
          </p>
        )}
      </section>

      <section className="delay" aria-label="Display delay">
        <DelayControl snapshot={snapshot} session={session} />
        <p className="hint">{DELAY_DISCLAIMER}</p>
        <p className="hint partial-availability" data-testid="partial-availability">
          {PARTIAL_AVAILABILITY_LABEL}
        </p>
      </section>
    </main>
  );
}

function DelayControl({
  snapshot,
  session,
}: {
  snapshot: SessionSnapshot;
  session: CaptionSession;
}): React.JSX.Element {
  const inputId = "display-delay";
  return (
    <div className="delay-control">
      <label htmlFor={inputId}>Display delay</label>
      <input
        id={inputId}
        type="range"
        min={0}
        max={5000}
        step={100}
        value={snapshot.delayMs}
        onChange={(event) => session.setDelay(Number(event.target.value))}
      />
      <output htmlFor={inputId} data-testid="delay-value">
        {snapshot.delayMs} ms
      </output>
    </div>
  );
}
