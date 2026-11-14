/**
 * Browser-safe shared entry for `@livecho/protocol`.
 *
 * This entry keeps the exact same strict parser, schema validation, JCS
 * projection and golden decision implementation as the Node entry
 * (`@livecho/protocol`), but swaps the environment adapters for browser
 * equivalents: `TextEncoder` for UTF-8 byte lengths and the pure synchronous
 * SHA-256 in `sha256.ts` for identity digests. No Node built-in import and no
 * runtime filesystem/schema read is reachable from this module.
 */
import { createProtocol, type Protocol } from "./core.js";
import { browserAdapters } from "./adapters/browser.js";

const protocol: Protocol = createProtocol(browserAdapters);

export {
  WORKER_PROTOCOL,
  VIEWER_PROTOCOL,
  PROTOCOL_MINOR,
  MAX_CONTROL_BYTES,
  canonicalJson,
} from "./core.js";
export type { StableCode, GoldenCaseV1, ProtocolAdapters, Protocol } from "./core.js";
export { sha256Hex } from "./sha256.js";

export const strictJsonParse: Protocol["strictJsonParse"] = protocol.strictJsonParse;
export const evaluateGoldenCase: Protocol["evaluateGoldenCase"] = protocol.evaluateGoldenCase;
export const isAcceptedCode: Protocol["isAcceptedCode"] = protocol.isAcceptedCode;
export const validateModel: Protocol["validateModel"] = protocol.validateModel;
