import { afterEach, describe, expect, it } from "vitest";
import http from "node:http";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { AppDatabase } from "../src/main/db";
import { JobManager } from "../src/main/jobs";
import { runTool } from "../src/main/tools";

const servers: http.Server[] = [];
afterEach(() => Promise.all(servers.map((server) => new Promise<void>((resolve) => server.close(() => resolve())))));

describe("persistent queue vertical slice", () => {
  it("extracts, downloads, validates, persists artifacts and completes", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-job-"));
    const fixture = path.join(root, "source.mp4");
    const generated = await runTool("ffmpeg", ["-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", fixture]);
    expect(generated.code).toBe(0);
    const payload = await fs.readFile(fixture);
    const server = http.createServer((request, response) => { response.writeHead(200, { "content-type": "video/mp4", "content-length": payload.length }); if (request.method !== "HEAD") response.end(payload); else response.end(); });
    servers.push(server); await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", () => resolve()));
    const port = (server.address() as { port: number }).port;
    const output = path.join(root, "output"); const db = new AppDatabase(path.join(root, "data")); const manager = new JobManager(db); manager.updateSettings({ downloadDir: output, concurrency: 1, perDomainConcurrency: 1 });
    const completed = new Promise<any>((resolve, reject) => { const timer = setTimeout(() => reject(new Error("queue timeout")), 5000); manager.on("changed", (job) => { if (job.status === "completed") { clearTimeout(timer); resolve(job); } if (job.status === "failed") { clearTimeout(timer); reject(new Error(JSON.stringify(job.error))); } }); });
    const created = manager.create({ sourceUrl: `http://127.0.0.1:${port}/fixture.mp4`, priority: 50 }); const job = await completed;
    expect(job.id).toBe(created.id); expect(job.progress).toBe(1); expect(db.listArtifacts(created.id).map((artifact: any) => artifact.kind)).toEqual(["downloaded", "final"]); expect((await fs.readFile(path.join(output, "fixture.mp4"))).equals(payload)).toBe(true);
    db.close(); await fs.rm(root, { recursive: true, force: true });
  });

  it("moves unsafe in-flight state back to queued during crash recovery", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-recovery-")); const db = new AppDatabase(root); const now = new Date().toISOString();
    db.saveJob({ id: "crashed", createdAt: now, updatedAt: now, sourceUrl: "https://example.com/file.mp4", destinationDir: root, status: "running", priority: 50, attempts: 1, maxAttempts: 3, progress: .4, bytesDownloaded: 40, totalBytes: 100 });
    const never = { extract: () => new Promise(() => {}) }; new JobManager(db, never as any); expect(db.getJob("crashed")?.status).toBe("queued"); await new Promise((resolve) => setTimeout(resolve, 0)); db.close(); await fs.rm(root, { recursive: true, force: true });
  });
});
