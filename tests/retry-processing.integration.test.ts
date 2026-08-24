import { describe, expect, it } from "vitest";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { AppDatabase } from "../src/main/db";
import { JobManager } from "../src/main/jobs";

describe("processing-only retry", () => {
  it("revalidates a retained artifact without contacting the source again", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "svp-process-retry-"));
    const retained = path.join(root, "retained.mp4");
    await fs.writeFile(retained, "invalid media retained for retry");
    const db = new AppDatabase(path.join(root, "data"));
    const now = new Date().toISOString();
    db.saveJob({ id: "retry", createdAt: now, updatedAt: now, sourceUrl: "http://127.0.0.1:1/offline.mp4", destinationDir: root, status: "failed", priority: 50, attempts: 1, maxAttempts: 3, progress: 1, bytesDownloaded: 32, totalBytes: 32, downloadedPath: retained });
    const manager = new JobManager(db);
    manager.command("retry", "retry");
    let result:any; for(let attempt=0;attempt<40;attempt++){result=db.getJob("retry");if(result?.status==="failed"&&result.attempts>1)break;await new Promise(resolve=>setTimeout(resolve,100));}
    expect(result?.status).toBe("failed");
    expect(result.error).toMatchObject({ code: "FINAL_INVALID", stage: "validate" });
    expect(await fs.readFile(retained, "utf8")).toContain("retained");
    db.close(); await fs.rm(root, { recursive: true, force: true });
  });
});
