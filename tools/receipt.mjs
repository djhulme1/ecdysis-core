// Ecdysis receipt id for a signed envelope: sha256 (hex) of the canonical
// JSON of {"p": payload, "s": signature} (keys sorted by UTF-16 code unit at
// every level, no whitespace, UTF-8), exactly as the server computes it.
// Usage: node tools/receipt.mjs projects/<slug>/envelope.json
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
const canon = (v) => Array.isArray(v) ? "[" + v.map(canon).join(",") + "]"
  : v !== null && typeof v === "object"
    ? "{" + Object.keys(v).sort().filter((k) => v[k] !== undefined).map((k) => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}"
    : JSON.stringify(v);
const env = JSON.parse(readFileSync(process.argv[2], "utf8"));
console.log(createHash("sha256").update(canon({ p: env.payload, s: env.signature }), "utf8").digest("hex"));
