/**
 * Generate an Ed25519 keypair on YOUR machine and print it, nothing else:
 *
 *   npx tsx scripts/keygen.ts            # prints public and private halves
 *   npx tsx scripts/keygen.ts --public   # prints only the public half
 *
 * The private half (PKCS#8, base64url) is a secret: install it where it
 * belongs (a Worker secret for the log key, a file beside your agent for
 * an agent key, a file on the runner for a check key) and back it up
 * offline. Never paste it into a chat or a session. The public half
 * (SPKI, base64url, starting MCowBQYDK2VwAyEA) is what you register.
 */
import { generateKeyPair } from "../src/core/crypto.js";

const kp = await generateKeyPair();
if (process.argv.includes("--public")) {
  process.stdout.write(`${kp.publicKey}\n`);
} else {
  process.stdout.write(`public  (register this):      ${kp.publicKey}\nprivate (keep this secret):   ${kp.privateKey}\n`);
}
