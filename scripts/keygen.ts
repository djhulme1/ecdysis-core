/**
 * Generate an Ed25519 keypair on YOUR machine, write the private half to a
 * file only you can read, and print the public half, nothing else:
 *
 *   npx tsx scripts/keygen.ts                       # writes ./ecdysis-key.pkcs8.b64url (mode 0600), prints the public half
 *   npx tsx scripts/keygen.ts path/to/agent.pkcs8   # the same, to that path (refuses to overwrite)
 *   npx tsx scripts/keygen.ts --public              # prints only a public half (and keeps nothing: for a dry run)
 *   npx tsx scripts/keygen.ts --print               # prints BOTH halves to stdout: only for a terminal nobody is logging
 *
 * The private half (PKCS#8, base64url) is a secret: it belongs in a file
 * beside your agent, on the runner for a check key, or in a Worker secret
 * for the log key, and in an offline backup. It never belongs in a chat, a
 * session transcript, a log or a repository, which is why the default
 * writes it to a file instead of the screen: a coding agent that runs this
 * script never sees it. The public half (SPKI, base64url, starting
 * MCowBQYDK2VwAyEA) is what you register.
 */
import { openSync, writeSync, closeSync } from "node:fs";
import { generateKeyPair } from "../src/core/crypto.js";

const args: string[] = process.argv.slice(2);
const kp = await generateKeyPair();
if (args.includes("--public")) {
  process.stdout.write(`${kp.publicKey}\n`);
} else if (args.includes("--print")) {
  process.stderr.write("Printing the private half: make sure nothing is recording this terminal.\n");
  process.stdout.write(`public  (register this):      ${kp.publicKey}\nprivate (keep this secret):   ${kp.privateKey}\n`);
} else {
  const path = args.find((a) => !a.startsWith("--")) ?? "ecdysis-key.pkcs8.b64url";
  const fd = ((): number | null => {
    try { return openSync(path, "wx", 0o600); } // create only: an existing key is never overwritten
    catch (e) {
      process.stderr.write(`Not written: ${path} ${(e as NodeJS.ErrnoException).code === "EEXIST" ? "already exists; choose another path or move it first" : `could not be created (${(e as Error).message})`}.\n`);
      return null;
    }
  })();
  if (fd === null) { process.exit(1); }
  else {
    writeSync(fd, `${kp.privateKey}\n`);
    closeSync(fd);
  }
  process.stdout.write(`${kp.publicKey}\n`);
  process.stderr.write(`Private half written to ${path} (readable by you alone). Register the public half above; back the file up offline.\n`);
}
