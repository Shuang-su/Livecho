import {
  bucket,
  defineRailway,
  postgres,
  preserve,
  project,
  ref,
  service,
  type VariableValue,
} from "railway/iac";

export const COMPUTE_REGION = "asia-southeast1-eqsg3a";
export const BUCKET_REGION = "sin";
export const BUILD_COMMAND = "make bootstrap && make build";

export const SAFETY_VARIABLES = Object.freeze({
  LIVECHO_GLOBAL_SERVING_ENABLED: "false",
  LIVECHO_INGEST_ENABLED: "false",
  LIVECHO_INGEST_MODE: "fixture",
  LIVECHO_PERSISTENCE_ENABLED: "false",
  LIVECHO_RAW_ARCHIVE_ENABLED: "false",
  LIVECHO_EMAIL_ENABLED: "false",
  LIVECHO_REAL_WORKER_AUDIO_ENABLED: "false",
  LIVECHO_MAINTENANCE_ENABLED: "false",
});

export const PERSISTENT_SECRET_SLOTS = Object.freeze([
  "LIVECHO_SESSION_SIGNING_KEY",
  "LIVECHO_WORKER_TOKEN_SIGNING_KEY",
  "LIVECHO_ARCHIVE_ENCRYPTION_KEY",
  "LIVECHO_RECOVERY_INTEGRITY_KEY",
  "LIVECHO_AUDIT_INTEGRITY_KEY",
  "RESEND_API_KEY",
] as const);

export type EnvironmentClass = "production" | "staging" | "unclassified-preview";

export function classifyEnvironment(environmentName: string | undefined): EnvironmentClass {
  if (environmentName === "production") {
    return "production";
  }
  if (environmentName === "staging") {
    return "staging";
  }
  return "unclassified-preview";
}

function persistentSecretVariables(environmentClass: EnvironmentClass): Record<string, VariableValue> {
  if (environmentClass === "unclassified-preview") {
    return {};
  }
  return Object.fromEntries(PERSISTENT_SECRET_SLOTS.map((name) => [name, preserve()]));
}

export default defineRailway((ctx) => {
  const environmentClass = classifyEnvironment(ctx.environmentName);
  const Postgres = postgres("Postgres", { region: COMPUTE_REGION });
  const Archive = bucket("Archive", { region: BUCKET_REGION });
  const regions = { [COMPUTE_REGION]: 1 };

  const web = service("web", {
    build: BUILD_COMMAND,
    start: "make railway-start-web",
    healthcheck: "/healthz",
    healthcheckTimeout: 30,
    regions,
  });

  const backend = service("backend", {
    build: BUILD_COMMAND,
    start: "make railway-start-backend",
    healthcheck: "/healthz",
    healthcheckTimeout: 30,
    regions,
    env: {
      ...SAFETY_VARIABLES,
      DATABASE_URL: Postgres.env.DATABASE_URL,
      BUCKET: ref(Archive, "BUCKET"),
      ENDPOINT: ref(Archive, "ENDPOINT"),
      REGION: ref(Archive, "REGION"),
      ACCESS_KEY_ID: ref(Archive, "ACCESS_KEY_ID"),
      SECRET_ACCESS_KEY: ref(Archive, "SECRET_ACCESS_KEY"),
      ...persistentSecretVariables(environmentClass),
    },
  });

  const maintenance = service("maintenance", {
    build: BUILD_COMMAND,
    start: "make railway-run-maintenance",
    regions,
    env: { ...SAFETY_VARIABLES },
    deploy: {
      restartPolicyType: "NEVER",
      drainingSeconds: 15,
    },
  });

  return project("livecho", {
    resources: [web, backend, Postgres, Archive, maintenance],
  });
});
