import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import { sha256Hex } from "./sha256.js";

describe("pure SHA-256 digest", () => {
  const vectors: Array<[string, string]> = [
    [
      "",
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ],
    ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
    [
      "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
      "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
    ],
    [
      "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
      "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1",
    ],
    ["a".repeat(1_000_000), "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"],
  ];

  for (const [input, expected] of vectors) {
    it(`matches the FIPS 180-4 vector for a ${input.length} byte message`, () => {
      expect(sha256Hex(input)).toBe(expected);
    });
  }

  it("matches node:crypto for arbitrary UTF-8 including astral characters", () => {
    const samples = [
      "livecho viewer timeline fixture",
      "字幕 partial\r\nline\u00a0break",
      "emoji \u{1f9ef} and combining \u0301",
      "x".repeat(65_536),
    ];
    for (const sample of samples) {
      expect(sha256Hex(sample)).toBe(
        createHash("sha256").update(sample, "utf8").digest("hex"),
      );
    }
  });
});
