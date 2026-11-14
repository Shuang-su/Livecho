import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import type { ProtocolAdapters } from "../core.js";

export const nodeAdapters: ProtocolAdapters = {
  byteLength(text) {
    return Buffer.byteLength(text, "utf8");
  },
  sha256Hex(text) {
    return createHash("sha256").update(text, "utf8").digest("hex");
  },
};
