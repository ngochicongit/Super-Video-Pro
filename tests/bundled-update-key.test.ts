import crypto from "node:crypto";
import fs from "node:fs";
import { describe, expect, it } from "vitest";

describe("bundled update verification key", () => {
  it("packages the expected parseable Ed25519 public key", () => {
    const pem = fs.readFileSync("assets/update-public.pem", "utf8");
    const key = crypto.createPublicKey(pem);
    expect(key.asymmetricKeyType).toBe("ed25519");
    const fingerprint = crypto.createHash("sha256").update(key.export({ type: "spki", format: "der" })).digest("hex");
    expect(fingerprint).toBe("5972a897b00c66f2a2fbc5d573b0db650315937540e8ac6e4351dd7c0864ea21");
    const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8")) as { build: { files: string[] } };
    expect(packageJson.build.files).toContain("assets/update-public.pem");
  });
});
