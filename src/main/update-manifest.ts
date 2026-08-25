import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
import { fetchOutbound, readBoundedText } from "./network-policy.js";

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
export const UpdateManifestPayloadSchema = SignedUpdateManifest.omit({ signature:true });

export type CreateUpdateManifestFileOptions = {
  installerPath: string;
  installerUrl: string;
  privateKeyPem: string;
  outputPath: string;
  version: string;
  channel: "stable" | "beta";
  publishedAt?: string;
};

export type SignedUpdateCheckResult = {
  available: boolean;
  manifest: SignedUpdateManifestType;
};

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

export function signUpdateManifest(input:unknown,privateKeyPem:string){const payload=UpdateManifestPayloadSchema.parse(input);const signature=crypto.sign(null,Buffer.from(canonicalUpdatePayload(payload)),privateKeyPem).toString("base64");return SignedUpdateManifest.parse({...payload,signature});}

export async function fetchSignedUpdateManifest(manifestUrl:string,publicKeyPem:string,signal?:AbortSignal){const url=HttpsUrl.parse(manifestUrl);const response=await fetchOutbound(url,{signal,headers:{accept:"application/json"}},15_000);if(!response.ok){await response.body?.cancel();throw new Error(`Update manifest request failed: HTTP ${response.status}`)}const text=await readBoundedText(response,64*1024);let raw:unknown;try{raw=JSON.parse(text)}catch{throw new Error("Update manifest is not valid JSON")}return verifySignedUpdateManifest(raw,publicKeyPem);}

function comparePrerelease(left: string | undefined, right: string | undefined) {
  if (left === right) return 0;
  if (left === undefined) return 1;
  if (right === undefined) return -1;
  const a = left.split(".");
  const b = right.split(".");
  for (let index = 0; index < Math.max(a.length, b.length); index++) {
    if (a[index] === undefined) return -1;
    if (b[index] === undefined) return 1;
    if (a[index] === b[index]) continue;
    const aNumber = /^\d+$/.test(a[index]) ? Number(a[index]) : undefined;
    const bNumber = /^\d+$/.test(b[index]) ? Number(b[index]) : undefined;
    if (aNumber !== undefined && bNumber !== undefined) return aNumber > bNumber ? 1 : -1;
    if (aNumber !== undefined) return -1;
    if (bNumber !== undefined) return 1;
    return a[index].localeCompare(b[index]);
  }
  return 0;
}

export function compareUpdateVersions(left: string, right: string) {
  const parse = (value: string) => {
    Semver.parse(value);
    const separator = value.indexOf("-");
    const core = separator === -1 ? value : value.slice(0, separator);
    const prerelease = separator === -1 ? undefined : value.slice(separator + 1);
    return { core: core.split(".").map(Number), prerelease };
  };
  const a = parse(left);
  const b = parse(right);
  for (let index = 0; index < 3; index++) if (a.core[index] !== b.core[index]) return a.core[index] > b.core[index] ? 1 : -1;
  return comparePrerelease(a.prerelease, b.prerelease);
}

export async function checkSignedUpdateAvailability(manifestUrl: string, publicKeyPem: string, currentVersion: string, signal?: AbortSignal): Promise<SignedUpdateCheckResult> {
  Semver.parse(currentVersion);
  const manifest = await fetchSignedUpdateManifest(manifestUrl, publicKeyPem, signal);
  return { available: compareUpdateVersions(manifest.version, currentVersion) > 0, manifest };
}

async function sha256File(filePath: string) {
  const hash = crypto.createHash("sha256");
  await new Promise<void>((resolve, reject) => {
    const stream = fs.createReadStream(filePath);
    stream.on("data", chunk => hash.update(chunk));
    stream.once("error", reject);
    stream.once("end", resolve);
  });
  return hash.digest("hex");
}

export async function createUpdateManifestFile(options: CreateUpdateManifestFileOptions) {
  const stat = await fs.promises.stat(options.installerPath);
  if (!stat.isFile() || stat.size <= 0) throw new Error("Installer must be a non-empty file");
  const payload: UpdateManifestPayload = {
    schemaVersion: 1,
    channel: options.channel,
    version: options.version,
    publishedAt: options.publishedAt ?? new Date().toISOString(),
    installerUrl: options.installerUrl,
    installerSha256: await sha256File(options.installerPath),
    installerSize: stat.size,
  };
  const manifest = signUpdateManifest(payload, options.privateKeyPem);
  const publicKeyPem = crypto.createPublicKey(options.privateKeyPem).export({ type: "spki", format: "pem" }).toString();
  verifySignedUpdateManifest(manifest, publicKeyPem);
  await fs.promises.mkdir(path.dirname(options.outputPath), { recursive: true });
  await fs.promises.writeFile(options.outputPath, `${JSON.stringify(manifest, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
  return manifest;
}

export async function verifyInstallerFile(filePath: string, manifest: Pick<SignedUpdateManifestType, "installerSha256" | "installerSize">) {
  const stat = await fs.promises.stat(filePath);
  if (stat.size !== manifest.installerSize) throw new Error(`Installer size mismatch: expected ${manifest.installerSize}, received ${stat.size}`);
  const actual = await sha256File(filePath);
  if (actual !== manifest.installerSha256.toLowerCase()) throw new Error(`Installer checksum mismatch: expected ${manifest.installerSha256.toLowerCase()}, received ${actual}`);
}
