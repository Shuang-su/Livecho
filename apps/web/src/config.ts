import { FIXTURE_PARTIAL_LABEL, UNKNOWN_PARTIAL_LABEL } from "./protocol/labels";

/**
 * Deployment-configured opaque room identifier. The page never accepts a URL
 * or an arbitrary ingest target from the route; a route parameter may only
 * repeat this configured room.
 */
export const CONFIGURED_ROOM_ID: string =
  (import.meta.env.VITE_LIVECHO_ROOM_ID as string | undefined) ?? "livecho.fixture.room";

export const VIEWER_SUPPORTED_MINORS: readonly (0 | 1)[] =
  import.meta.env.VITE_LIVECHO_VIEWER_MINOR_1 === "1" ? [0, 1] : [0];

/**
 * Truthful partial availability text for the demonstration configuration.
 * This fixture timeline exercises v1 partial revisions, so the final-only
 * label does not apply; real worker partial output stays unconfirmed.
 */
export const PARTIAL_AVAILABILITY_LABEL: string =
  import.meta.env.VITE_LIVECHO_PARTIAL_LABEL === "final-only"
    ? "Final subtitles only; partial unavailable"
    : import.meta.env.VITE_LIVECHO_PARTIAL_LABEL === "unknown"
      ? UNKNOWN_PARTIAL_LABEL
      : FIXTURE_PARTIAL_LABEL;

const ROOM_ID_PATTERN = /^[a-z0-9][a-z0-9._:-]{0,127}$/u;

export interface RoomSelection {
  ok: boolean;
  roomId: string;
}

/**
 * Resolve the room for this view from the optional `/r/<room>` route segment.
 * Anything other than the configured room renders an unavailable-room page
 * and never connects; a malformed `/r/...` path is also refused.
 */
export function resolveRequestedRoom(pathname: string, configuredRoom: string): RoomSelection {
  if (pathname === "/" || pathname === "") return { ok: true, roomId: configuredRoom };
  const match = /^\/r\/([^/]+)\/?$/.exec(pathname);
  if (match === null) {
    return pathname.startsWith("/r/") ? { ok: false, roomId: configuredRoom } : { ok: true, roomId: configuredRoom };
  }
  const requested = decodeURIComponent(match[1] ?? "");
  if (!ROOM_ID_PATTERN.test(requested) || requested !== configuredRoom) {
    return { ok: false, roomId: configuredRoom };
  }
  return { ok: true, roomId: requested };
}
