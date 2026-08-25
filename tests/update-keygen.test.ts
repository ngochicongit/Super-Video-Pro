import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { describe, expect, it } from "vitest";

function runKeygen(outputDirectory: string) {
  return new Promise<{ code: number; stdout: string; stderr: string }>((resolve, reject) => {
    const child = spawn(process.execPath, ["scripts/generate-update-keypair.mjs", outputDirectory], { cwd: process.cwd(), windowsHide: true });
    let stdout = ""; let stderr = "";
    child.stdout.on("data", chunk => stdout += String(chunk));
    child.stderr.on("data", chunk => stderr += String(chunk));
    child.once("error", reject);
    child.once("close", code => resolve({ code: code ?? -1, stdout, stderr }));
  });
}

describe("update key generation", () => {
  it("creates a usable pair outside the repository without printing the private key", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-keygen-"));
    try {
      const result = await runKeygen(root);
      expect(result.code).toBe(0);
      expect(result.stdout).not.toContain("BEGIN PRIVATE KEY");
      const privateKey = await fs.readFile(path.join(root, "svp-update-private.pem"), "utf8");
      const publicKey = await fs.readFile(path.join(root, "svp-update-public.pem"), "utf8");
      const message = Buffer.from("signed-update-proof");
      const signature = crypto.sign(null, message, privateKey);
      expect(crypto.verify(null, message, publicKey, signature)).toBe(true);
      await expect(runKeygen(root)).resolves.toMatchObject({ code: 1 });
    } finally {
      await fs.rm(root, { recursive: true, force: true });
    }
  });

  it("refuses to create signing keys inside the repository", async () => {
    const target = path.join(process.cwd(), "outputs", "unsafe-keygen");
    await expect(runKeygen(target)).resolves.toMatchObject({ code: 1 });
    await expect(fs.stat(target)).rejects.toMatchObject({ code: "ENOENT" });
  });
});
