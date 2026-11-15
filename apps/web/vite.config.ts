import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const SHELL_ALLOWLIST_PLACEHOLDER = "__LIVECHO_SHELL_ALLOWLIST__";
const SHELL_VERSION_PLACEHOLDER = "__LIVECHO_SHELL_VERSION__";

/**
 * Build-produced static shell allowlist for the service worker.
 *
 * After Vite emits the production bundle, every file below `dist/` is by
 * construction part of the versioned application shell, so the plugin lists
 * exactly those files and inlines the list (plus a shell version digest) into
 * `dist/sw.js`. Nothing outside this list — APIs, WebSocket traffic, unknown
 * URLs — is ever cacheable by the service worker.
 */
function shellAllowlist(): Plugin {
  return {
    name: "livecho-shell-allowlist",
    apply: "build",
    closeBundle() {
      const dist = join(import.meta.dirname, "dist");
      const files: string[] = [];
      const walk = (directory: string): void => {
        for (const entry of readdirSync(directory).sort()) {
          const path = join(directory, entry);
          if (statSync(path).isDirectory()) walk(path);
          else files.push(`/${relative(dist, path)}`);
        }
      };
      walk(dist);
      const allowlist = JSON.stringify(files);
      const version = [...allowlist]
        .reduce((hash, character) => (hash * 33 + character.charCodeAt(0)) >>> 0, 5381)
        .toString(16)
        .padStart(8, "0");
      const swPath = join(dist, "sw.js");
      const source = readFileSync(swPath, "utf8");
      // Minifiers may rewrite quote characters, so match any quote style and
      // also a bare version token embedded inside the cache name template.
      const parsedAllowlist = new RegExp(
        `JSON\\.parse\\((["'\`])${SHELL_ALLOWLIST_PLACEHOLDER}\\1\\)`,
        "u",
      );
      const quotedVersion = new RegExp(`(["'\`])${SHELL_VERSION_PLACEHOLDER}\\1`, "u");
      if (!parsedAllowlist.test(source) || !source.includes(SHELL_VERSION_PLACEHOLDER)) {
        throw new Error("service worker bundle did not contain the shell allowlist placeholders");
      }
      const rewritten = source
        .replace(parsedAllowlist, allowlist)
        .replace(quotedVersion, JSON.stringify(version))
        .replaceAll(SHELL_VERSION_PLACEHOLDER, version);
      if (rewritten === source) {
        throw new Error("service worker allowlist rewrite produced no change");
      }
      writeFileSync(swPath, rewritten);
    },
  };
}

export default defineConfig({
  plugins: [react(), shellAllowlist()],
  resolve: {
    alias: [
      {
        find: "@livecho/protocol/browser",
        replacement: join(import.meta.dirname, "../../packages/protocol/src/browser.ts"),
      },
    ],
  },
  build: {
    rollupOptions: {
      input: { main: join(import.meta.dirname, "index.html"), sw: join(import.meta.dirname, "src/pwa/sw.ts") },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === "sw" ? "sw.js" : "assets/[name]-[hash].js",
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "ws://127.0.0.1:8787",
        ws: true,
      },
    },
  },
});
