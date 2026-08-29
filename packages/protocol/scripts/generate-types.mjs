import { readFile, writeFile } from "node:fs/promises";
import { compile } from "json-schema-to-typescript";

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  throw new Error("usage: generate-types.mjs <schema> <output>");
}

const schema = JSON.parse(await readFile(inputPath, "utf8"));
const generated = await compile(schema, "ProtocolMessageV1", {
  bannerComment: "",
  declareExternallyReferenced: true,
  enableConstEnums: false,
  format: true,
  ignoreMinAndMaxItems: true,
  strictIndexSignatures: true,
  unreachableDefinitions: true,
});
await writeFile(outputPath, `${generated.trimEnd()}\n`, "utf8");
