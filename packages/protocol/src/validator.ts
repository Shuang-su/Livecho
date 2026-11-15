import { createProtocol, type Protocol } from "./core.js";
import { nodeAdapters } from "./adapters/node.js";

const protocol: Protocol = createProtocol(nodeAdapters);

export {
  WORKER_PROTOCOL,
  VIEWER_PROTOCOL,
  PROTOCOL_MINOR,
  MAX_CONTROL_BYTES,
  canonicalJson,
} from "./core.js";
export type { StableCode, GoldenCaseV1, ProtocolAdapters } from "./core.js";

export const strictJsonParse: Protocol["strictJsonParse"] = protocol.strictJsonParse;
export const evaluateGoldenCase: Protocol["evaluateGoldenCase"] = protocol.evaluateGoldenCase;
export const isAcceptedCode: Protocol["isAcceptedCode"] = protocol.isAcceptedCode;
export const validateModel: Protocol["validateModel"] = protocol.validateModel;
