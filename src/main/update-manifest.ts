import crypto from "node:crypto";
import fs from "node:fs";
import { z } from "zod";

const Sha256 = z.string().regex(/^[a-f0-9]{64}$/i);
const HttpsUrl = z.string().url().refine(value => new URL(value).protocol === "https:", "HTTPS is required");
const Semver = z.string().regex(/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/);

export const SignedUpdateManifest = z.object({
  schemaVersion: z.literal(1),
  channel: z.enum(["stable", "beta"]),
  version: Semver,
  publishedAt: z.string().datetime(),
  installerUrl: HttpsUrl,
  installerSha256: Sha256,
  installerSize: z.number().int().positive(),
  minimumSupportedVersion: Semver.optional(),
  releaseNotesUrl: HttpsUrl.optional(),
  signature: z.string().min(1),
}).strict();

export type SignedUpdateManifestType = z.infer<typeof SignedUpdateManifest>;
export type UpdateManifestPayload = Omit<SignedUpdateManifestType, "signature">;

export function canonicalUpdatePayload(payload: UpdateManifestPayload) {
  return JSON.stringify({
    schemaVersion: payload.schemaVersion,
    channel: payload.channel,
    version: payload.version,
    publishedAt: payload.publishedAt,
    installerUrl: payload.installerUrl,
    installerSha256: payload.installerSha256.toLowerCase(),
    installerSize: payload.installerSize,
    ...(payload.minimumSupportedVersion === undefined ? {} : { minimumSupportedVersion: payload.minimumSupportedVersion }),
    ...(payload.releaseNotesUrl === undefined ? {} : { releaseNotesUrl: payload.releaseNotesUrl }),
  });
}

export function verifySignedUpdateManifest(input: unknown, publicKeyPem: string) {
  const manifest = SignedUpdateManifest.parse(input);
  const { signature, ...payload } = manifest;
  const verified = crypto.verify(null, Buffer.from(canonicalUpdatePayload(payload)), publicKeyPem, Buffer.from(signature, "base64"));
  if (!verified) throw new Error("Update manifest signature is invalid");
  return manifest;
}

export async function verifyInstallerFile(filePath: string, manifest: Pick<SignedUpdateManifestType, "installerSha256" | "installerSize">) {
  const stat = await fs.promises.stat(filePath);
  if (stat.size !== manifest.installerSize) throw new Error(`Installer size mismatch: expected ${manifest.installerSize}, received ${stat.size}`);
  const hash = crypto.createHash("sha256");
  await new Promise<void>((resolve, reject) => {
    const stream = fs.createReadStream(filePath);
    stream.on("data", chunk => hash.update(chunk));
    stream.once("error", reject);
    stream.once("end", resolve);
  });
  const actual = hash.digest("hex");
  if (actual !== manifest.installerSha256.toLowerCase()) throw new Error(`Installer checksum mismatch: expected ${manifest.installerSha256.toLowerCase()}, received ${actual}`);
}
