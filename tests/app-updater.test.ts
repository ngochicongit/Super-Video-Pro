import crypto from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { canonicalUpdatePayload, type UpdateManifestPayload } from "../src/main/update-manifest";

const { autoUpdaterMock } = vi.hoisted(() => ({
  autoUpdaterMock: {
    autoDownload: true,
    autoInstallOnAppQuit: true,
    on: vi.fn(),
    setFeedURL: vi.fn(),
    checkForUpdates: vi.fn(),
    downloadUpdate: vi.fn(),
    quitAndInstall: vi.fn(),
  },
}));

vi.mock("electron-updater", () => ({ default: { autoUpdater: autoUpdaterMock } }));

import { AppUpdater, anyUpdateCheckConfigured } from "../src/main/app-updater";

const originalEnvironment = { ...process.env };
afterEach(() => {
  process.env = { ...originalEnvironment };
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("runtime signed update boundary", () => {
  it("surfaces incomplete signed configuration without falling back", async () => {
    process.env.SVP_SIGNED_UPDATE_MANIFEST_URL = "https://updates.example.com/manifest.json";
    delete process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM;
    process.env.SVP_UPDATE_FEED_URL = "https://legacy.example.com";
    expect(anyUpdateCheckConfigured()).toBe(true);
    await expect(new AppUpdater("1.2.9").check()).resolves.toMatchObject({ state: "error" });
    expect(autoUpdaterMock.setFeedURL).not.toHaveBeenCalled();
  });

  it("checks authentic metadata but blocks download and install handoff", async () => {
    const keys = crypto.generateKeyPairSync("ed25519");
    const payload: UpdateManifestPayload = { schemaVersion: 1, channel: "stable", version: "1.3.0", publishedAt: "2026-08-25T00:00:00.000Z", installerUrl: "https://updates.example.com/app.exe", installerSha256: "a".repeat(64), installerSize: 100 };
    const signature = crypto.sign(null, Buffer.from(canonicalUpdatePayload(payload)), keys.privateKey).toString("base64");
    process.env.SVP_SIGNED_UPDATE_MANIFEST_URL = "https://updates.example.com/manifest.json";
    process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM = keys.publicKey.export({ type: "spki", format: "pem" }).toString();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ...payload, signature }), { status: 200 })));
    const updater = new AppUpdater("1.2.9");
    await expect(updater.check()).resolves.toMatchObject({ state: "available", version: "1.3.0" });
    await expect(updater.download()).rejects.toThrow("disabled for personal distribution");
    expect(() => updater.install()).toThrow("disabled for personal distribution");
    expect(autoUpdaterMock.downloadUpdate).not.toHaveBeenCalled();
    expect(autoUpdaterMock.quitAndInstall).not.toHaveBeenCalled();
  });
});
