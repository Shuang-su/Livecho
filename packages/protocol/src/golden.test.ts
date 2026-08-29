import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { evaluateGoldenCase, isAcceptedCode, type GoldenCaseV1 } from "./validator.js";

interface Manifest {
  accepted: string[];
  rejected: string[];
  version: number;
}

function loadCases(): GoldenCaseV1[] {
  const fixtureRoot = new URL("../fixtures/", import.meta.url);
  const manifest = JSON.parse(
    readFileSync(new URL("manifest.json", fixtureRoot), "utf8"),
  ) as Manifest;
  return [...manifest.accepted, ...manifest.rejected].map(
    (path) => JSON.parse(readFileSync(new URL(path, fixtureRoot), "utf8")) as GoldenCaseV1,
  );
}

describe("protocol v1 golden parity", () => {
  const cases = loadCases();

  it("loads one deterministic result for every generated case", () => {
    expect(cases).toHaveLength(117);
    expect(new Set(cases.map((testCase) => testCase.case_id)).size).toBe(cases.length);
  });

  for (const testCase of cases) {
    it(testCase.case_id, () => {
      const result = evaluateGoldenCase(testCase);
      expect(result).toBe(testCase.code);
      expect(isAcceptedCode(result)).toBe(testCase.expect === "accepted");
    });
  }
});
