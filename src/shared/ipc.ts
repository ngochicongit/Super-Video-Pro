import { z } from "zod";
import { AppSettings, AppSettingsPatch, ClearJobsInput, CompositionIdInput, CompositionJob, CompositionSpec, CreateJobInput, DiagnosticsExportInput, DownloadJob, InspectMediaInput, JobIdInput, ListJobsInput, MediaResource, PickCompositionInput, ShowItemInput, UiLogInput, WindowActionInput } from "./contracts.js";
export const ipcContract = {
  "app:get-info": { input: z.object({}).default({}), output: z.object({ version: z.string(), platform: z.string(), updatesConfigured: z.boolean() }) },
  "settings:get": { input: z.object({}).default({}), output: AppSettings },
  "settings:update": { input: AppSettingsPatch, output: AppSettings },
  "dialog:download-dir": { input: z.object({}).default({}), output: z.string().nullable() },
  "dialog:composition-input": { input: PickCompositionInput, output: z.string().nullable() },
  "dialog:composition-videos": { input: z.object({}).strict().default({}), output: z.array(z.string()).max(19) },
  "shell:show-item": { input: ShowItemInput, output: z.object({ shown: z.boolean() }) },
  "window:control": { input: WindowActionInput, output: z.object({ maximized: z.boolean() }) },
  "app:log-action": { input: UiLogInput, output: z.object({ logged: z.boolean() }) },
  "diagnostics:export": { input: DiagnosticsExportInput, output: z.string().nullable() },
  "evidence:gate": { input: z.object({}).default({}), output: z.object({passed:z.boolean(),activeDays:z.number().int().nonnegative(),bounceRate:z.number().nonnegative(),thresholds:z.object({minimumActiveDays:z.number(),minimumMultiInputIntents:z.number(),minimumCompletedExports:z.number(),maximumBounceRate:z.number()}),summary:z.record(z.string(),z.object({count:z.number().int().nonnegative(),activeDays:z.number().int().nonnegative()}))}) },
  "evidence:multi-input-intent": { input: z.object({}).strict().default({}), output: z.object({recorded:z.boolean(),gate:z.object({passed:z.boolean(),activeDays:z.number().int().nonnegative(),bounceRate:z.number().nonnegative(),thresholds:z.object({minimumActiveDays:z.number(),minimumMultiInputIntents:z.number(),minimumCompletedExports:z.number(),maximumBounceRate:z.number()}),summary:z.record(z.string(),z.object({count:z.number().int().nonnegative(),activeDays:z.number().int().nonnegative()}))})}) },
  "evidence:export": { input: z.object({}).default({}), output: z.string().nullable() },
  "compositions:list": { input: z.object({}).default({}), output: z.array(CompositionJob) },
  "compositions:create": { input: CompositionSpec, output: CompositionJob },
  "compositions:cancel": { input: CompositionIdInput, output: CompositionJob },
  "compositions:retry": { input: CompositionIdInput, output: CompositionJob },
  "compositions:remove": { input: CompositionIdInput, output: z.object({ removed: z.boolean() }) },
  "tools:status": { input: z.object({}).default({}), output: z.array(z.object({name:z.string(),available:z.boolean(),version:z.string().nullable()})) },
  "updates:check": { input: z.object({}).default({}), output: z.object({state:z.string(),version:z.string().optional(),percent:z.number().optional(),message:z.string().optional()}) },
  "updates:status": { input: z.object({}).default({}), output: z.object({state:z.string(),version:z.string().optional(),percent:z.number().optional(),message:z.string().optional()}) },
  "updates:download": { input: z.object({}).default({}), output: z.object({state:z.string(),version:z.string().optional(),percent:z.number().optional(),message:z.string().optional()}) },
  "updates:install": { input: z.object({}).default({}), output: z.object({accepted:z.boolean()}) },
  "media:inspect": { input: InspectMediaInput, output: MediaResource },
  "jobs:list": { input: ListJobsInput, output: z.array(DownloadJob) },
  "jobs:create": { input: CreateJobInput, output: DownloadJob },
  "jobs:pause": { input: JobIdInput, output: DownloadJob },
  "jobs:resume": { input: JobIdInput, output: DownloadJob },
  "jobs:cancel": { input: JobIdInput, output: DownloadJob },
  "jobs:retry": { input: JobIdInput, output: DownloadJob }
  ,"jobs:remove": { input: JobIdInput, output: z.object({ removed: z.boolean() }) }
  ,"jobs:clear-terminal": { input: ClearJobsInput, output: z.object({ removed: z.number().int().nonnegative() }) }
} as const;
export type IpcChannel = keyof typeof ipcContract;
