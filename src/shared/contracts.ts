import { z } from "zod";
const HttpUrl=z.string().url().refine(value=>{const protocol=new URL(value).protocol;return protocol==="http:"||protocol==="https:"},{message:"Only HTTP(S) URLs are allowed"});

export const ProtectionStatus = z.enum(["none", "unknown", "protected", "unsupported"]);
export const MediaVariant = z.object({
  id: z.string(), url: HttpUrl, container: z.string().optional(), protocol: z.enum(["http", "hls", "dash", "external"]),
  width: z.number().int().positive().optional(), height: z.number().int().positive().optional(), bitrate: z.number().positive().optional(),
  audioOnly: z.boolean().default(false), label: z.string().optional()
});
export const MediaResource = z.object({
  version: z.literal(1), sourceUrl: HttpUrl, title: z.string().min(1), extractor: z.string(),
  protection: ProtectionStatus.default("unknown"), variants: z.array(MediaVariant),
  subtitles: z.array(z.object({ language: z.string(), url: HttpUrl, format: z.string().optional() })).default([]),
  metadata: z.record(z.string(), z.unknown()).default({})
});
export type MediaResource = z.infer<typeof MediaResource>;

export const JobStatus = z.enum(["queued", "running", "paused", "retrying", "processing", "validating", "failed", "completed", "cancelled"]);
export const DownloadJob = z.object({
  id: z.string(), createdAt: z.string().datetime(), updatedAt: z.string().datetime(), sourceUrl: HttpUrl,
  destinationDir: z.string().min(1), selectedVariantId: z.string().optional(), status: JobStatus,
  priority: z.number().int().min(0).max(100).default(50), attempts: z.number().int().nonnegative().default(0), maxAttempts: z.number().int().positive().default(3),
  progress: z.number().min(0).max(1).default(0), bytesDownloaded: z.number().nonnegative().default(0), totalBytes: z.number().positive().nullable().default(null),
  resource: MediaResource.optional(), downloadedPath: z.string().optional(), error: z.unknown().optional()
});
export type DownloadJob = z.infer<typeof DownloadJob>;

export const MediaArtifact = z.object({
  id: z.string(), jobId: z.string(), kind: z.enum(["partial", "downloaded", "processed", "invalid"]), path: z.string(),
  size: z.number().nonnegative(), sha256: z.string().optional(), createdAt: z.string().datetime(),
  validation: z.object({ valid: z.boolean(), container: z.string().optional(), durationSeconds: z.number().nonnegative().optional(), streams: z.array(z.string()).default([]), reasons: z.array(z.string()).default([]) })
});
export type MediaArtifact = z.infer<typeof MediaArtifact>;
export const FinalArtifact = z.object({
  id: z.string(), jobId: z.string(), sourceArtifactIds: z.array(z.string()).min(1), path: z.string(), displayName: z.string(),
  size: z.number().nonnegative(), createdAt: z.string().datetime(), container: z.string().optional(), durationSeconds: z.number().nonnegative().optional()
});
export type FinalArtifact = z.infer<typeof FinalArtifact>;

export const InspectMediaInput=z.object({sourceUrl:HttpUrl}).strict();
export const CreateJobInput = z.object({ sourceUrl: HttpUrl, destinationDir: z.string().min(1).optional(), priority: z.number().int().min(0).max(100).default(50),selectedVariantId:z.string().optional(),resource:MediaResource.optional() }).strict();
export const JobIdInput = z.object({ jobId: z.string().min(1) });
export const ClearJobsInput = z.object({ statuses: z.array(z.enum(["completed", "cancelled"])).min(1).default(["completed", "cancelled"]) }).default({ statuses: ["completed", "cancelled"] });
export const ShowItemInput = z.object({ path: z.string().min(1) }).strict();
export const WindowActionInput = z.object({ action: z.enum(["minimize", "toggle-maximize", "close"]) }).strict();
export const UiLogInput = z.object({ action: z.string().min(1).max(80), details: z.record(z.string(), z.union([z.string(),z.number(),z.boolean(),z.null()])).default({}) }).strict();
export const ListJobsInput = z.object({ limit: z.number().int().min(1).max(500).default(100) }).default({ limit: 100 });
export const AppSettings = z.object({ downloadDir: z.string(), concurrency: z.number().int().min(1).max(8), perDomainConcurrency: z.number().int().min(1).max(4), cookiesFromBrowser: z.enum(["none","edge","chrome","firefox"]).default("none"),allowThirdPartyXFallback:z.boolean().default(false),collectProductEvidence:z.boolean().default(false),historyRetentionDays:z.number().int().min(1).max(3650).default(90),logRetentionDays:z.number().int().min(1).max(365).default(30),backupRetentionCount:z.number().int().min(1).max(10).default(3),rememberUiState:z.boolean().default(true),lastSourceInput:z.string().max(10000).default(""),downloadMode:z.enum(["single","batch"]).default("single"),queueSearch:z.string().max(200).default(""),queueStatusFilter:z.union([z.literal("all"),JobStatus]).default("all"),recentUrls:z.array(HttpUrl).max(30).default([]),diagnosticsFileName:z.string().max(120).default("") });
export type AppSettings = z.infer<typeof AppSettings>;
export const AppSettingsPatch=z.object({downloadDir:z.string().optional(),concurrency:z.number().int().min(1).max(8).optional(),perDomainConcurrency:z.number().int().min(1).max(4).optional(),cookiesFromBrowser:z.enum(["none","edge","chrome","firefox"]).optional(),allowThirdPartyXFallback:z.boolean().optional(),collectProductEvidence:z.boolean().optional(),historyRetentionDays:z.number().int().min(1).max(3650).optional(),logRetentionDays:z.number().int().min(1).max(365).optional(),backupRetentionCount:z.number().int().min(1).max(10).optional(),rememberUiState:z.boolean().optional(),lastSourceInput:z.string().max(10000).optional(),downloadMode:z.enum(["single","batch"]).optional(),queueSearch:z.string().max(200).optional(),queueStatusFilter:z.union([z.literal("all"),JobStatus]).optional(),recentUrls:z.array(HttpUrl).max(30).optional(),diagnosticsFileName:z.string().max(120).optional()}).strict();
export const DiagnosticsExportInput=z.object({fileName:z.string().trim().max(120).optional()}).strict().default({});
