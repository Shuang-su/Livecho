import { execFileSync, spawnSync } from "node:child_process";
import {
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { createServer } from "node:net";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

type RailwayModule = typeof import("./railway.js");
type IacModule = typeof import("railway/iac");
type ProjectDefinition = Awaited<ReturnType<RailwayModule["default"]>>;
type ResourceNode = NonNullable<ProjectDefinition["resources"]>[number] extends infer Resource
  ? Resource extends readonly unknown[]
    ? Resource[number]
    : Resource
  : never;

const railwayRoot = fileURLToPath(new URL(".", import.meta.url));
const repositoryRoot = dirname(railwayRoot);
const makefilePath = join(repositoryRoot, "Makefile");

const SOURCE_ALLOWLIST = Object.freeze([
  ".railway/package.json",
  ".railway/railway.test.ts",
  ".railway/railway.ts",
  ".railway/tsconfig.json",
]);

const temporaryRepositories: string[] = [];

function splitNul(value: string): string[] {
  return value.split("\0").filter((entry) => entry.length > 0);
}

function fail(message: string): never {
  throw new Error(message);
}

export function assertRailwaySourceTree(root: string): void {
  const candidateRoot = join(root, ".railway");
  const rootStat = lstatSync(candidateRoot);
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) {
    fail(".railway must be a real, non-symlink directory");
  }

  const discovered = splitNul(
    execFileSync(
      "git",
      ["ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", ".railway"],
      { cwd: root, encoding: "utf8" },
    ),
  ).sort();
  if (JSON.stringify(discovered) !== JSON.stringify([...SOURCE_ALLOWLIST].sort())) {
    fail(`unexpected .railway Git-visible entries: ${JSON.stringify(discovered)}`);
  }

  const staged = splitNul(
    execFileSync("git", ["ls-files", "--stage", "-z", "--", ".railway"], {
      cwd: root,
      encoding: "utf8",
    }),
  );
  for (const record of staged) {
    const separator = record.indexOf("\t");
    if (separator < 0) {
      fail("unparseable Git index record under .railway");
    }
    const [mode, , stage] = record.slice(0, separator).split(" ");
    const path = record.slice(separator + 1);
    if (!SOURCE_ALLOWLIST.includes(path)) {
      fail(`unexpected tracked .railway path: ${JSON.stringify(path)}`);
    }
    if ((mode !== "100644" && mode !== "100755") || stage !== "0") {
      fail(`unsafe Git index mode or stage for ${path}: ${mode} stage ${stage}`);
    }
  }

  for (const path of SOURCE_ALLOWLIST) {
    const stat = lstatSync(join(root, path));
    if (stat.isSymbolicLink() || !stat.isFile()) {
      fail(`${path} must be a real, non-symlink regular file`);
    }
  }

  for (const entry of readdirSync(candidateRoot)) {
    const relativePath = `.railway/${entry}`;
    const stat = lstatSync(join(candidateRoot, entry));
    if (entry === "node_modules") {
      if (stat.isSymbolicLink() || !stat.isDirectory()) {
        fail(".railway/node_modules may be pruned only when it is a real directory");
      }
      continue;
    }
    if (!SOURCE_ALLOWLIST.includes(relativePath)) {
      fail(`unexpected physical .railway entry: ${JSON.stringify(relativePath)}`);
    }
    if (stat.isSymbolicLink() || !stat.isFile()) {
      fail(`${relativePath} must be a real, non-symlink regular file`);
    }
  }
}

function initializeSourceFixture(): string {
  const root = mkdtempSync(join(tmpdir(), "livecho-railway-source-"));
  temporaryRepositories.push(root);
  execFileSync("git", ["init", "--quiet"], { cwd: root });
  execFileSync("git", ["config", "user.email", "source-guard@example.invalid"], { cwd: root });
  execFileSync("git", ["config", "user.name", "Source Guard"], { cwd: root });
  writeFileSync(join(root, ".gitignore"), "node_modules/\n");
  mkdirSync(join(root, ".railway"));
  for (const path of SOURCE_ALLOWLIST) {
    writeFileSync(join(root, path), path.endsWith(".json") ? "{}\n" : "export {};\n");
  }
  execFileSync("git", ["add", "--", ".railway"], { cwd: root });
  return root;
}

function runMigration(root: string) {
  return spawnSync("make", ["--no-print-directory", "-f", makefilePath, "railway-migrate"], {
    cwd: root,
    encoding: "utf8",
  });
}

async function withUnixSocket(path: string, callback: () => void): Promise<void> {
  const server = createServer();
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(path, resolve);
  });
  try {
    callback();
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error === undefined ? resolve() : reject(error)));
    });
  }
}

let railway: RailwayModule;
let iac: IacModule;

beforeAll(async () => {
  assertRailwaySourceTree(repositoryRoot);
  [railway, iac] = await Promise.all([import("./railway.js"), import("railway/iac")]);
});

afterEach(() => {
  while (temporaryRepositories.length > 0) {
    const root = temporaryRepositories.pop();
    if (root !== undefined) {
      rmSync(root, { recursive: true, force: true });
    }
  }
});

async function render(input: { environmentName?: string } = {}): Promise<ProjectDefinition> {
  const rendered = await railway.default(iac.createRailwayContext(input), iac.project);
  return JSON.parse(JSON.stringify(rendered)) as ProjectDefinition;
}

function resourcesOf(definition: ProjectDefinition): ResourceNode[] {
  return (definition.resources ?? []).flat() as ResourceNode[];
}

function resourceNamed(definition: ProjectDefinition, name: string): ResourceNode {
  const matches = resourcesOf(definition).filter((resource) => resource.name === name);
  expect(matches).toHaveLength(1);
  const match = matches[0];
  if (match === undefined) {
    throw new Error(`missing resource ${name}`);
  }
  return match;
}

function expectedLiteralSafetyVariables() {
  return Object.fromEntries(
    Object.entries(railway.SAFETY_VARIABLES).map(([name, value]) => [
      name,
      { type: "literal", value },
    ]),
  );
}

describe("environment classification", () => {
  it.each([
    ["production", "production"],
    ["staging", "staging"],
    ["pr-123", "unclassified-preview"],
    ["arbitrary", "unclassified-preview"],
    ["", "unclassified-preview"],
    [undefined, "unclassified-preview"],
    ["Production", "unclassified-preview"],
    [" staging", "unclassified-preview"],
    ["staging ", "unclassified-preview"],
  ] as const)("classifies %s exactly", (name, expected) => {
    expect(railway.classifyEnvironment(name)).toBe(expected);
  });

  it("does not read process environment variables", async () => {
    const baseline = await render({ environmentName: "pr-123" });
    const priorProduction = process.env.RAILWAY_ENVIRONMENT_NAME;
    const priorClass = process.env.LIVECHO_ENVIRONMENT_CLASS;
    process.env.RAILWAY_ENVIRONMENT_NAME = "production";
    process.env.LIVECHO_ENVIRONMENT_CLASS = "production";
    try {
      expect(await render({ environmentName: "pr-123" })).toEqual(baseline);
    } finally {
      if (priorProduction === undefined) delete process.env.RAILWAY_ENVIRONMENT_NAME;
      else process.env.RAILWAY_ENVIRONMENT_NAME = priorProduction;
      if (priorClass === undefined) delete process.env.LIVECHO_ENVIRONMENT_CLASS;
      else process.env.LIVECHO_ENVIRONMENT_CLASS = priorClass;
    }
  });
});

describe.each([
  ["production", { environmentName: "production" }, true],
  ["staging", { environmentName: "staging" }, true],
  ["PR render policy only", { environmentName: "pr-123" }, false],
  ["arbitrary preview", { environmentName: "arbitrary" }, false],
  ["empty preview", { environmentName: "" }, false],
  ["missing preview", {}, false],
] as const)("desired-state graph for %s", (_label, input, persistent) => {
  it("renders the exact fail-closed topology and contracts", async () => {
    const definition = await render(input);
    expect(definition.name).toBe("livecho");
    expect(resourcesOf(definition).map(({ type, name }) => [type, name])).toEqual([
      ["service", "web"],
      ["service", "backend"],
      ["database", "Postgres"],
      ["bucket", "Archive"],
      ["service", "maintenance"],
    ]);

    expect(resourceNamed(definition, "web")).toEqual({
      address: "service.web",
      type: "service",
      kind: "empty",
      name: "web",
      build: { buildCommand: railway.BUILD_COMMAND },
      deploy: {
        startCommand: "make railway-start-web",
        healthcheckPath: "/healthz",
        healthcheckTimeout: 30,
        multiRegionConfig: {
          [railway.COMPUTE_REGION]: { numReplicas: 1 },
        },
      },
    });

    const persistentVariables = persistent
      ? Object.fromEntries(railway.PERSISTENT_SECRET_SLOTS.map((name) => [name, { type: "preserve" }]))
      : {};
    expect(resourceNamed(definition, "backend")).toEqual({
      address: "service.backend",
      type: "service",
      kind: "empty",
      name: "backend",
      build: { buildCommand: railway.BUILD_COMMAND },
      deploy: {
        startCommand: "make railway-start-backend",
        healthcheckPath: "/healthz",
        healthcheckTimeout: 30,
        multiRegionConfig: {
          [railway.COMPUTE_REGION]: { numReplicas: 1 },
        },
      },
      variables: {
        ...expectedLiteralSafetyVariables(),
        DATABASE_URL: {
          type: "reference",
          resource: "database.Postgres",
          output: "DATABASE_URL",
        },
        BUCKET: { type: "reference", resource: "bucket.Archive", output: "BUCKET" },
        ENDPOINT: { type: "reference", resource: "bucket.Archive", output: "ENDPOINT" },
        REGION: { type: "reference", resource: "bucket.Archive", output: "REGION" },
        ACCESS_KEY_ID: {
          type: "reference",
          resource: "bucket.Archive",
          output: "ACCESS_KEY_ID",
        },
        SECRET_ACCESS_KEY: {
          type: "reference",
          resource: "bucket.Archive",
          output: "SECRET_ACCESS_KEY",
        },
        ...persistentVariables,
      },
    });

    expect(resourceNamed(definition, "Postgres")).toEqual({
      address: "database.Postgres",
      type: "database",
      kind: "database",
      engine: "postgres",
      name: "Postgres",
      image: "ghcr.io/railwayapp-templates/postgres-ssl:18",
      output: "DATABASE_URL",
      defaultMountPath: "/var/lib/postgresql/data",
      source: {
        type: "image",
        image: "ghcr.io/railwayapp-templates/postgres-ssl:18",
      },
      deploy: {
        multiRegionConfig: {
          [railway.COMPUTE_REGION]: { numReplicas: 1 },
        },
      },
    });

    expect(resourceNamed(definition, "Archive")).toEqual({
      address: "bucket.Archive",
      type: "bucket",
      name: "Archive",
      config: { region: railway.BUCKET_REGION },
    });

    expect(resourceNamed(definition, "maintenance")).toEqual({
      address: "service.maintenance",
      type: "service",
      kind: "empty",
      name: "maintenance",
      build: { buildCommand: railway.BUILD_COMMAND },
      deploy: {
        restartPolicyType: "NEVER",
        drainingSeconds: 15,
        startCommand: "make railway-run-maintenance",
        multiRegionConfig: {
          [railway.COMPUTE_REGION]: { numReplicas: 1 },
        },
      },
      variables: expectedLiteralSafetyVariables(),
    });
  });

  it("is deterministic for the same synthetic context", async () => {
    expect(await render(input)).toEqual(await render(input));
  });
});

describe("Railway source and tree guard", () => {
  it("accepts only the reviewed current tree", () => {
    expect(() => assertRailwaySourceTree(repositoryRoot)).not.toThrow();
  });

  it("rejects a symlinked .railway root before Git traversal", () => {
    const root = initializeSourceFixture();
    renameSync(join(root, ".railway"), join(root, ".railway-real"));
    symlinkSync(".railway-real", join(root, ".railway"));
    expect(() => assertRailwaySourceTree(root)).toThrow(/real, non-symlink directory/);
  });

  it.each(["valid", "dangling"])("rejects a %s allowlisted-file symlink", (kind) => {
    const root = initializeSourceFixture();
    const path = join(root, ".railway", "railway.ts");
    unlinkSync(path);
    if (kind === "valid") {
      writeFileSync(join(root, "target.ts"), "export {};\n");
      symlinkSync("../target.ts", path);
    } else {
      symlinkSync("../missing.ts", path);
    }
    expect(() => assertRailwaySourceTree(root)).toThrow(/regular file/);
  });

  it("rejects a symlinked node_modules root", () => {
    const root = initializeSourceFixture();
    mkdirSync(join(root, "dependencies"));
    symlinkSync("../dependencies", join(root, ".railway", "node_modules"));
    expect(() => assertRailwaySourceTree(root)).toThrow(/unexpected|may be pruned only/);
  });

  it("permits package-manager links only below a real node_modules directory", () => {
    const root = initializeSourceFixture();
    mkdirSync(join(root, ".railway", "node_modules"));
    mkdirSync(join(root, "dependencies"));
    symlinkSync("../../dependencies", join(root, ".railway", "node_modules", "dependency"));
    expect(() => assertRailwaySourceTree(root)).not.toThrow();
  });

  it("rejects a tracked symlink index mode materialized as a regular file", () => {
    const root = initializeSourceFixture();
    const path = join(root, ".railway", "railway.ts");
    unlinkSync(path);
    symlinkSync("../target.ts", path);
    execFileSync("git", ["add", "--", ".railway/railway.ts"], { cwd: root });
    execFileSync("git", ["config", "core.symlinks", "false"], { cwd: root });
    unlinkSync(path);
    writeFileSync(path, "../target.ts");
    expect(() => assertRailwaySourceTree(root)).toThrow(/unsafe Git index mode/);
  });

  it.each([
    "railway.json",
    "railway.toml",
    "railway.py",
    "railway.go",
    ".railway-link.json",
    "provider-state",
    "generated.cache",
    "Railway-extra.ts",
    "line\nbreak",
  ])("rejects an ignored or untracked physical entry %s", (entry) => {
    const root = initializeSourceFixture();
    writeFileSync(join(root, ".gitignore"), ".railway/*state*\n.railway/*.cache\n");
    writeFileSync(join(root, ".railway", entry), "forbidden\n");
    expect(() => assertRailwaySourceTree(root)).toThrow(/unexpected/);
  });
});

describe("local safety and Make contracts", () => {
  it("keeps .env.example to the exact eight safe assignments", () => {
    const content = readFileSync(join(repositoryRoot, ".env.example"), "utf8");
    expect(content).toBe(
      Object.entries(railway.SAFETY_VARIABLES)
        .map(([name, value]) => `${name}=${value}`)
        .join("\n") + "\n",
    );
    expect(content.split("\n").filter(Boolean)).toHaveLength(8);
    expect(content).not.toMatch(/^\s*#/m);
    expect(content).not.toMatch(/(?:PASSWORD|TOKEN|COOKIE|PRIVATE_KEY|DATABASE_URL)=/);
  });

  it("pins the offline workspace and denies dependency install scripts", () => {
    const manifest = JSON.parse(readFileSync(join(railwayRoot, "package.json"), "utf8")) as {
      name: string;
      private: boolean;
      dependencies: Record<string, string>;
      devDependencies: Record<string, string>;
      scripts: Record<string, string>;
    };
    expect(manifest).toMatchObject({
      name: "@livecho/railway-config",
      private: true,
      dependencies: { railway: "3.11.0" },
      devDependencies: {
        "@types/node": "26.4.0",
        typescript: "7.0.2",
        vitest: "4.1.11",
      },
    });
    expect(Object.keys(manifest.dependencies)).toEqual(["railway"]);
    expect(Object.keys(manifest.devDependencies).sort()).toEqual([
      "@types/node",
      "typescript",
      "vitest",
    ]);
    expect(Object.keys(manifest.scripts).sort()).toEqual(["build", "lint", "test", "typecheck"]);
    expect(JSON.stringify(manifest)).not.toContain("@railway/cli");

    const workspace = readFileSync(join(repositoryRoot, "pnpm-workspace.yaml"), "utf8");
    expect(workspace).not.toMatch(/(?:allowBuilds|onlyBuiltDependencies):/);
    const makefile = readFileSync(makefilePath, "utf8");
    expect(makefile).toContain("pnpm install --frozen-lockfile --ignore-scripts");
    const lockfile = readFileSync(join(repositoryRoot, "pnpm-lock.yaml"), "utf8");
    expect(lockfile).not.toContain("@railway/cli");
  });

  it.each([
    ["railway-start-web", "Issue #11"],
    ["railway-start-backend", "Issue #9"],
    ["railway-run-maintenance", "No approved maintenance operation"],
  ])("keeps %s as a non-zero, side-effect-free guard", (target, message) => {
    const root = mkdtempSync(join(tmpdir(), "livecho-railway-start-"));
    temporaryRepositories.push(root);
    const before = readdirSync(root);
    const result = spawnSync("make", ["--no-print-directory", "-f", makefilePath, target], {
      cwd: root,
      encoding: "utf8",
      env: { PATH: process.env.PATH ?? "" },
    });
    expect(result.status).not.toBe(0);
    expect(`${result.stdout}${result.stderr}`).toContain(message);
    expect(readdirSync(root)).toEqual(before);
  });

  it("declares every Railway target phony and contains no provider mutation automation", () => {
    const makefile = readFileSync(makefilePath, "utf8");
    const phony = makefile.match(/^\.PHONY:\s+(.+)$/m)?.[1]?.split(/\s+/) ?? [];
    expect(phony).toEqual(
      expect.arrayContaining([
        "railway-check",
        "railway-start-web",
        "railway-start-backend",
        "railway-run-maintenance",
        "railway-migrate",
      ]),
    );
    const executableConfiguration = [
      makefile,
      readFileSync(join(repositoryRoot, "package.json"), "utf8"),
      readFileSync(join(railwayRoot, "package.json"), "utf8"),
      readFileSync(join(repositoryRoot, ".github", "workflows", "verify.yml"), "utf8"),
    ].join("\n");
    for (const forbidden of [
      "railway " + "up",
      "config " + "apply",
      "environment " + "delete",
      "railway " + "down",
      "--show-" + "values",
      "--include-" + "variables",
      "@railway/" + "cli",
    ]) {
      expect(executableConfiguration).not.toContain(forbidden);
    }
  });

  it.each(["railway.json", "railway.toml", "railway.py", "railway.go"])(
    "has no second Railway authoring file named %s",
    (name) => {
      expect(() => lstatSync(join(railwayRoot, name))).toThrow();
    },
  );
});

describe("railway-migrate no-schema guard", () => {
  it("succeeds only when both db or its migrations final entry are absent", () => {
    for (const withDb of [false, true]) {
      const root = mkdtempSync(join(tmpdir(), "livecho-railway-migrate-"));
      temporaryRepositories.push(root);
      if (withDb) mkdirSync(join(root, "db"));
      const result = runMigration(root);
      expect(result.status).toBe(0);
      expect(result.stdout.trim()).toBe("NO_MIGRATIONS");
    }
  });

  it.each(["file", "fifo", "valid-symlink", "dangling-symlink"])(
    "rejects a db parent that is a %s",
    (kind) => {
      const root = mkdtempSync(join(tmpdir(), "livecho-railway-db-parent-"));
      temporaryRepositories.push(root);
      const path = join(root, "db");
      if (kind === "file") writeFileSync(path, "not a directory\n");
      if (kind === "fifo") execFileSync("mkfifo", [path]);
      if (kind === "valid-symlink") {
        mkdirSync(join(root, "outside"));
        symlinkSync("outside", path);
      }
      if (kind === "dangling-symlink") symlinkSync("missing", path);
      const result = runMigration(root);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain("db must be a real, non-symlink directory");
    },
  );

  it.each([false, true])(
    "rejects a symlinked db parent without following an outside target (migrations=%s)",
    (withMigrations) => {
      const root = mkdtempSync(join(tmpdir(), "livecho-railway-db-outside-"));
      temporaryRepositories.push(root);
      mkdirSync(join(root, "outside"));
      if (withMigrations) mkdirSync(join(root, "outside", "migrations"));
      symlinkSync("outside", join(root, "db"));
      const result = runMigration(root);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain("db must be a real, non-symlink directory");
    },
  );

  it("rejects a db parent that is a Unix socket", async () => {
    const root = mkdtempSync(join(tmpdir(), "livecho-railway-db-socket-"));
    temporaryRepositories.push(root);
    await withUnixSocket(join(root, "db"), () => {
      const result = runMigration(root);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain("db must be a real, non-symlink directory");
    });
  });

  it.each(["file", "empty-directory", "nonempty-directory", "fifo", "valid-symlink", "dangling-symlink"])(
    "rejects an existing migrations final entry that is a %s",
    (kind) => {
      const root = mkdtempSync(join(tmpdir(), "livecho-railway-migrations-"));
      temporaryRepositories.push(root);
      const db = join(root, "db");
      const path = join(db, "migrations");
      mkdirSync(db);
      if (kind === "file") writeFileSync(path, "not a migration root\n");
      if (kind === "empty-directory") mkdirSync(path);
      if (kind === "nonempty-directory") {
        mkdirSync(path);
        writeFileSync(join(path, "001.sql"), "select 1;\n");
      }
      if (kind === "fifo") execFileSync("mkfifo", [path]);
      if (kind === "valid-symlink") {
        mkdirSync(join(root, "outside"));
        symlinkSync("../../outside", path);
      }
      if (kind === "dangling-symlink") symlinkSync("../../missing", path);
      const result = runMigration(root);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain("db/migrations exists");
    },
  );

  it("rejects a migrations final entry that is a Unix socket", async () => {
    const root = mkdtempSync(join(tmpdir(), "livecho-railway-migrations-socket-"));
    temporaryRepositories.push(root);
    mkdirSync(join(root, "db"));
    await withUnixSocket(join(root, "db", "migrations"), () => {
      const result = runMigration(root);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain("db/migrations exists");
    });
  });
});
