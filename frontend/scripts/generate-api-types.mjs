import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

const source = readFileSync(new URL("../../docs/openapi.json", import.meta.url), "utf8").replace(/\r\n/g, "\n");
const schema = JSON.parse(source);
function typeOf(value = {}) {
  if (value.$ref) return value.$ref.split("/").at(-1);
  if (value.enum) return value.enum.map((item) => JSON.stringify(item)).join(" | ");
  if (value.anyOf || value.oneOf) return (value.anyOf ?? value.oneOf).map(typeOf).join(" | ");
  if (value.allOf) return value.allOf.map(typeOf).join(" & ");
  if (value.type === "null") return "null";
  if (value.type === "string") return "string";
  if (["integer", "number"].includes(value.type)) return "number";
  if (value.type === "boolean") return "boolean";
  if (value.type === "array") return `Array<${typeOf(value.items)}>`;
  if (value.properties) {
    const fields = Object.entries(value.properties).map(([name, child]) => `${JSON.stringify(name)}${value.required?.includes(name) ? "" : "?"}: ${typeOf(child)};`);
    if (value.additionalProperties) fields.push(`[key: string]: ${typeof value.additionalProperties === "object" ? typeOf(value.additionalProperties) : "unknown"};`);
    return `{ ${fields.join(" ")} }`;
  }
  if (value.type === "object") return "Record<string, unknown>";
  return "unknown";
}
const hash = createHash("sha256").update(source).digest("hex");
const rendered = `// Generated from docs/openapi.json (SHA-256 ${hash}). Do not edit.\n` +
  Object.entries(schema.components?.schemas ?? {}).sort(([a], [b]) => a.localeCompare(b)).map(([name, value]) => `export type ${name} = ${typeOf(value)};`).join("\n") + "\n";
const target = new URL("../generated/api-types.ts", import.meta.url);
if (process.argv.includes("--check")) {
  if (readFileSync(target, "utf8").replace(/\r\n/g, "\n") !== rendered) { process.stderr.write("Generated API types are stale. Run npm run generate:api.\n"); process.exit(1); }
} else {
  mkdirSync(fileURLToPath(new URL("../generated/", import.meta.url)), { recursive: true });
  writeFileSync(target, rendered);
}
