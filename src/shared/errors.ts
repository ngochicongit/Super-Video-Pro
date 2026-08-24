import { z } from "zod";
export const ErrorStage = z.enum(["input", "extract", "download", "process", "validate", "storage", "security", "internal"]);
export type NormalizedError = { code: string; stage: z.infer<typeof ErrorStage>; message: string; retryable: boolean; rawCode?: string; details?: unknown };
const known: Record<string, Omit<NormalizedError, "details">> = {
  INVALID_INPUT: { code: "INVALID_INPUT", stage: "input", message: "Input is invalid.", retryable: false },
  UNSUPPORTED_MEDIA: { code: "UNSUPPORTED_MEDIA", stage: "extract", message: "No supported media was found.", retryable: false },
  NETWORK_TIMEOUT: { code: "NETWORK_TIMEOUT", stage: "download", message: "The network request timed out.", retryable: true },
  LOW_DISK: { code: "LOW_DISK", stage: "storage", message: "Not enough free disk space.", retryable: true },
  TOOL_MISSING: { code: "TOOL_MISSING", stage: "internal", message: "A required runtime tool is not installed or available.", retryable: false },
  FINAL_INVALID: { code: "FINAL_INVALID", stage: "validate", message: "The final media file failed validation.", retryable: false },
  CANCELLED: { code: "CANCELLED", stage: "download", message: "The operation was cancelled.", retryable: false }
};
export function normalizeError(error: unknown, stage: NormalizedError["stage"] = "internal"): NormalizedError {
  const candidate = error as { code?: unknown; name?: unknown; message?: unknown } | null;
  const rawCode = typeof candidate?.code === "string" ? candidate.code : typeof candidate?.name === "string" ? candidate.name : undefined;
  if (rawCode && known[rawCode]) return { ...known[rawCode], rawCode, details: error };
  return { code: "UNKNOWN", rawCode, stage, message: typeof candidate?.message === "string" ? candidate.message : "An unexpected error occurred.", retryable: false, details: error };
}
