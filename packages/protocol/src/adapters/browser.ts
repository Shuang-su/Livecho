import type { ProtocolAdapters } from "../core.js";
import { sha256Hex } from "../sha256.js";

const encoder = new TextEncoder();

export const browserAdapters: ProtocolAdapters = {
  byteLength(text) {
    return encoder.encode(text).length;
  },
  sha256Hex,
};
