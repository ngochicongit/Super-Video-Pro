import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { canonicalUpdatePayload, verifyInstallerFile, verifySignedUpdateManifest, type UpdateManifestPayload } from "../src/main/update-manifest";

function signedManifest(overrides: Partial<UpdateManifestPayload> = {}) {
  const keys = crypto.generateKeyPairSync("ed25519");
  const payload: UpdateManifestPayload = {
    schemaVersion: 1,
    channel: "stable",
    version: "1.2.9",
    publishedAt: "2026-08-25T00:00:00.000Z",
    installerUrl: "https://updates.example.com/Super-Video-Pro-1.2.9.exe",
    installerSha256: "a".repeat(64),
    installerSize: 123,
    ...overrides,
  };
  const signature = crypto.sign(null, Buffer.from(canonicalUpdatePayload(payload)), keys.privateKey).toString("base64");
  return { manifest: { ...payload, signature }, publicKey: keys.publicKey.export({ type: "spki", format: "pem" }).toString() };
}

describe("signed update manifest", () => {
  it("accepts an authentic Ed25519 manifest", () => {
    const { manifest, publicKey } = signedManifest();
    expect(verifySignedUpdateManifest(manifest, publicKey).version).toBe("1.2.9");
  });

  it("rejects metadata tampering", () => {
    const { manifest, publicKey } = signedManifest();
    expect(() => verifySignedUpdateManifest({ ...manifest, installerSize: 124 }, publicKey)).toThrow("signature is invalid");
  });

  it("rejects insecure installer URLs and unknown fields", () => {
    const { manifest, publicKey } = signedManifest();
    expect(() => verifySignedUpdateManifest({ ...manifest, installerUrl: "http://updates.example.com/app.exe" }, publicKey)).toThrow();
    expect(() => verifySignedUpdateManifest({ ...manifest, unexpected: true }, publicKey)).toThrow();
  });

  it("verifies installer size and SHA-256", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-update-manifest-"));
    const installer = path.join(root, "installer.exe");
    const data = Buffer.from("verified-installer");
    await fs.writeFile(installer, data);
    const expected = { installerSize: data.length, installerSha256: crypto.createHash("sha256").update(data).digest("hex") };
    await expect(verifyInstallerFile(installer, expected)).resolves.toBeUndefined();
    await expect(verifyInstallerFile(installer, { ...expected, installerSha256: "0".repeat(64) })).rejects.toThrow("checksum mismatch");
    await fs.rm(root, { recursive: true, force: true });
  });
});
