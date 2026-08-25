import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const outputArgument = process.argv[2];
if (!outputArgument) throw new Error("Usage: pnpm release:keygen -- <output-directory-outside-repository>");

const workspace = path.resolve(".");
const outputDirectory = path.resolve(outputArgument);
const relative = path.relative(workspace, outputDirectory);
if (relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative))) {
  throw new Error("Update signing keys must be created outside the repository");
}

await fs.mkdir(outputDirectory, { recursive: true, mode: 0o700 });
const privateKeyPath = path.join(outputDirectory, "svp-update-private.pem");
const publicKeyPath = path.join(outputDirectory, "svp-update-public.pem");
const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
const privateKeyPem = privateKey.export({ type: "pkcs8", format: "pem" });
const publicKeyPem = publicKey.export({ type: "spki", format: "pem" });

try {
  await fs.writeFile(privateKeyPath, privateKeyPem, { flag: "wx", mode: 0o600 });
  try {
    await fs.writeFile(publicKeyPath, publicKeyPem, { flag: "wx", mode: 0o644 });
  } catch (error) {
    await fs.rm(privateKeyPath, { force: true });
    throw error;
  }
} catch (error) {
  if (error && typeof error === "object" && "code" in error && error.code === "EEXIST") {
    throw new Error("Refusing to overwrite an existing update key pair");
  }
  throw error;
}

const fingerprint = crypto.createHash("sha256").update(publicKey.export({ type: "spki", format: "der" })).digest("hex");
console.log(`Created Ed25519 update key pair outside the repository.`);
console.log(`Private key: ${privateKeyPath}`);
console.log(`Public key: ${publicKeyPath}`);
console.log(`Public key SHA-256: ${fingerprint}`);
console.log("The private key content was not printed. Keep it private and backed up securely.");
