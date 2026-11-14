/** Type surface for the fixture server double (implementation in fixture-server.mjs). */
export interface FixtureServerOptions {
  root: string;
  host: string;
  port: number;
  room: string;
  segments: number;
  intervalMs: number;
  stopAt: number;
  stopReason: string;
  failAt: number;
  deleteAt: number;
  closeAt: number;
  refuseResume: boolean;
  noPartials: boolean;
  staticOnly: boolean;
}

export interface FixtureTimelineInfo {
  sessionId: string;
  status: string;
  nextSeq: string;
}

export interface FixtureServerHandle {
  httpServer: import("node:http").Server;
  timeline: FixtureTimelineInfo & {
    subscribers: Set<unknown>;
    status: string;
  };
  close(): Promise<void>;
}

export function createFixtureServer(options: FixtureServerOptions): FixtureServerHandle;
export function parseArguments(argv: string[]): FixtureServerOptions;
