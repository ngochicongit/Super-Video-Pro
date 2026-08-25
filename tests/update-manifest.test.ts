import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { canonicalUpdatePayload, checkSignedUpdateAvailability, compareUpdateVersions, createUpdateManifestFile, fetchSignedUpdateManifest, signUpdateManifest, verifyInstallerFile, verifySignedUpdateManifest, type UpdateManifestPayload } from "../src/main/update-manifest";

afterEach(()=>vi.unstubAllGlobals());

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

  it("signs a validated payload for release tooling",()=>{const keys=crypto.generateKeyPairSync("ed25519");const {manifest}=signedManifest();const {signature:_signature,...payload}=manifest;const privateKey=keys.privateKey.export({type:"pkcs8",format:"pem"}).toString();const publicKey=keys.publicKey.export({type:"spki",format:"pem"}).toString();expect(verifySignedUpdateManifest(signUpdateManifest(payload,privateKey),publicKey).version).toBe("1.2.9");});

  it("fetches only a bounded HTTPS manifest and verifies it",async()=>{const {manifest,publicKey}=signedManifest();vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify(manifest),{status:200,headers:{"content-type":"application/json"}})));await expect(fetchSignedUpdateManifest("https://updates.example.com/manifest.json",publicKey)).resolves.toMatchObject({version:"1.2.9"});await expect(fetchSignedUpdateManifest("http://updates.example.com/manifest.json",publicKey)).rejects.toThrow("HTTPS is required");});

  it("rejects oversized update metadata before parsing",async()=>{const {publicKey}=signedManifest();vi.stubGlobal("fetch",vi.fn(async()=>new Response("{}",{headers:{"content-length":String(64*1024+1)}})));await expect(fetchSignedUpdateManifest("https://updates.example.com/manifest.json",publicKey)).rejects.toThrow("byte limit");});

  it("rejects metadata tampering", () => {
    const { manifest, publicKey } = signedManifest();
    expect(() => verifySignedUpdateManifest({ ...manifest, installerSize: 124 }, publicKey)).toThrow("signature is invalid");
  });

  it("rejects insecure installer URLs and unknown fields", () => {
    const { manifest, publicKey } = signedManifest();
    expect(() => verifySignedUpdateManifest({ ...manifest, installerUrl: "http://updates.example.com/app.exe" }, publicKey)).toThrow();
    expect(() => verifySignedUpdateManifest({ ...manifest, unexpected: true }, publicKey)).toThrow();
  });

  it("compares stable and prerelease versions deterministically",()=>{expect(compareUpdateVersions("1.3.0","1.2.9")).toBeGreaterThan(0);expect(compareUpdateVersions("1.2.9","1.2.9")).toBe(0);expect(compareUpdateVersions("1.2.9-beta.2","1.2.9-beta.1")).toBeGreaterThan(0);expect(compareUpdateVersions("1.2.9-alpha-beta","1.2.9-alpha-alpha")).toBeGreaterThan(0);expect(compareUpdateVersions("1.2.9","1.2.9-beta.2")).toBeGreaterThan(0);expect(()=>compareUpdateVersions("latest","1.2.9")).toThrow();});

  it("reports availability only after authentic signed metadata verifies",async()=>{const {manifest,publicKey}=signedManifest({version:"1.3.0"});vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify(manifest),{status:200})));await expect(checkSignedUpdateAvailability("https://updates.example.com/manifest.json",publicKey,"1.2.8")).resolves.toMatchObject({available:true,manifest:{version:"1.3.0"}});await expect(checkSignedUpdateAvailability("https://updates.example.com/manifest.json",publicKey,"1.3.0")).resolves.toMatchObject({available:false});});

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

  it("creates a signed manifest without overwriting an existing candidate", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-update-create-"));
    try {
      const installerPath = path.join(root, "installer.exe");
      const outputPath = path.join(root, "candidate", "update-manifest.json");
      const installer = Buffer.from("streamed-installer-content");
      const keys = crypto.generateKeyPairSync("ed25519");
      const privateKeyPem = keys.privateKey.export({ type: "pkcs8", format: "pem" }).toString();
      const publicKeyPem = keys.publicKey.export({ type: "spki", format: "pem" }).toString();
      await fs.writeFile(installerPath, installer);

      const manifest = await createUpdateManifestFile({
        installerPath,
        installerUrl: "https://updates.example.com/installer.exe",
        privateKeyPem,
        outputPath,
        version: "1.2.8",
        channel: "stable",
        publishedAt: "2026-08-25T00:00:00.000Z",
      });

      expect(manifest.installerSize).toBe(installer.length);
      expect(manifest.installerSha256).toBe(crypto.createHash("sha256").update(installer).digest("hex"));
      expect(verifySignedUpdateManifest(JSON.parse(await fs.readFile(outputPath, "utf8")), publicKeyPem)).toEqual(manifest);
      await expect(createUpdateManifestFile({
        installerPath,
        installerUrl: "https://updates.example.com/installer.exe",
        privateKeyPem,
        outputPath,
        version: "1.2.8",
        channel: "stable",
      })).rejects.toMatchObject({ code: "EEXIST" });
    } finally {
      await fs.rm(root, { recursive: true, force: true });
    }
  });
});
