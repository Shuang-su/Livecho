import { useEffect, useState, useSyncExternalStore } from "react";
import { CaptionSession, type SessionDeps, type SessionSnapshot } from "../protocol/session";

/**
 * Create one caption session for the mounted view and dispose it on unmount.
 * Session state is memory-only; nothing here touches browser storage.
 */
export function useCaptionSession(deps: SessionDeps): CaptionSession {
  const [session] = useState(() => new CaptionSession(deps));
  useEffect(() => {
    return () => {
      session.dispose();
    };
  }, [session]);
  return session;
}

export function useSessionSnapshot(session: CaptionSession): SessionSnapshot {
  return useSyncExternalStore(
    (listener) => session.subscribe(listener),
    () => session.getSnapshot(),
  );
}
