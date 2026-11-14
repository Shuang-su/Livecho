#!/usr/bin/env node
/**
 * Static browser-entry safety check for @livecho/protocol.
 *
 * Walks the TypeScript import graph reachable from src/browser.ts and fails
 * when any Node built-in module (or the Node adapter/entry) is reachable, or
 * when the browser entry does not reach the shared core implementation.
 */
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const entry = join(packageRoot, "src", "browser.ts");
const core = join(packageRoot, "src", "core.ts");
const forbiddenExact = new Set([
  join(packageRoot, "src", "validator.ts"),
  join(packageRoot, "src", "adapters", "node.ts"),
  join(packageRoot, "src", "index.ts"),
]);
const nodeBuiltins = new Set([
  "assert", "buffer", "child_process", "cluster", "console", "constants", "crypto",
  "dgram", "dns", "domain", "events", "fs", "http", "http2", "https", "inspector",
  "module", "net", "os", "path", "perf_hooks", "process", "punycode", "querystring",
  "readline", "repl", "stream", "string_decoder", "timers", "tls", "trace_events",
  "tty", "url", "util", "v8", "vm", "worker_threads", "zlib",
]);

const importPattern = /(?:from\s*|import\s*\(?\s*)(["'])([^"']+)\1/g;

function resolveSpecifier(fromFile, specifier) {
  if (!specifier.startsWith(".")) return null;
  const base = resolve(dirname(fromFile), specifier);
  const candidates = specifier.endsWith(".js")
    ? [base, base.slice(0, -3) + ".ts"]
    : [base, `${base}.ts`, `${base}.tsx`];
  for (const candidate of candidates) {
    try {
      readFileSync(candidate);
      return candidate;
    } catch {
      // try the next candidate
    }
  }
  throw new Error(`unresolvable relative import ${specifier} in ${fromFile}`);
}

function importedSpecifiers(file) {
  const text = readFileSync(file, "utf8");
  const specifiers = [];
  for (const match of text.matchAll(importPattern)) {
    specifiers.push(match[2]);
  }
  return specifiers;
}

const visited = new Set();
const queue = [entry];
const errors = [];
while (queue.length > 0) {
  const file = queue.pop();
  if (visited.has(file)) continue;
  visited.add(file);
  if (forbiddenExact.has(file)) {
    errors.push(`browser entry reaches Node-only module: ${file}`);
    continue;
  }
  for (const specifier of importedSpecifiers(file)) {
    if (specifier.startsWith("node:")) {
      errors.push(`browser entry imports Node built-in ${specifier} in ${file}`);
      continue;
    }
    const bare = specifier.split("/")[0];
    if (nodeBuiltins.has(bare)) {
      errors.push(`browser entry imports Node built-in ${specifier} in ${file}`);
      continue;
    }
    const resolved = resolveSpecifier(file, specifier);
    if (resolved !== null && !visited.has(resolved)) queue.push(resolved);
  }
}

if (!visited.has(core)) {
  errors.push("browser entry does not reach the shared core implementation");
}

if (errors.length > 0) {
  for (const error of errors) console.error(error);
  process.exit(1);
}
console.log(
  `browser entry: ok (${visited.size} modules, no Node built-ins, shared core reachable)`,
);
