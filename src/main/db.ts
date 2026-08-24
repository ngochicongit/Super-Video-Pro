import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import fs from "node:fs";
import { DownloadJob, FinalArtifact, MediaArtifact, type DownloadJob as DownloadJobType } from "../shared/contracts.js";

export class AppDatabase {
  private db: DatabaseSync;
  constructor(private dataDir: string) {
    fs.mkdirSync(dataDir, { recursive: true });
    const dbPath=path.join(dataDir,"super-video-pro.sqlite");const existed=fs.existsSync(dbPath)&&fs.statSync(dbPath).size>0;
    this.db = new DatabaseSync(dbPath);
    this.db.exec("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;");
    const version=Number((this.db.prepare("PRAGMA user_version").get() as {user_version:number}).user_version);if(existed&&version<1){this.db.exec("PRAGMA wal_checkpoint(TRUNCATE)");this.db.close();fs.copyFileSync(dbPath,`${dbPath}.backup-v${version}-to-v1`);this.db=new DatabaseSync(dbPath);this.db.exec("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;");}
    this.migrate();
  }
  private migrate() {
    this.db.exec(`CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, status TEXT NOT NULL, priority INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status, priority DESC, created_at ASC);
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE, kind TEXT NOT NULL, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS quarantined_records(entity TEXT NOT NULL, record_id TEXT NOT NULL, raw_payload TEXT NOT NULL, error TEXT NOT NULL, quarantined_at TEXT NOT NULL, PRIMARY KEY(entity, record_id));
      INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (1, datetime('now'));
      PRAGMA user_version = 1;`);
  }
  private quarantine(entity:"jobs"|"artifacts"|"settings",id:string,payload:string,error:unknown){const message=error instanceof Error?error.message:String(error);this.db.prepare("INSERT INTO quarantined_records(entity,record_id,raw_payload,error,quarantined_at) VALUES(?,?,?,?,datetime('now')) ON CONFLICT(entity,record_id) DO UPDATE SET raw_payload=excluded.raw_payload,error=excluded.error,quarantined_at=excluded.quarantined_at").run(entity,id,payload,message);const table=entity;const key=entity==="settings"?"key":"id";this.db.prepare(`DELETE FROM ${table} WHERE ${key}=?`).run(id);}
  quarantineSetting(key:string,value:unknown,error:unknown){this.quarantine("settings",key,JSON.stringify(value),error);}
  private parseJob(id:string,payload:string):DownloadJobType|undefined{try{const parsed=DownloadJob.safeParse(JSON.parse(payload));if(parsed.success)return parsed.data;this.quarantine("jobs",id,payload,parsed.error);return undefined}catch(error){this.quarantine("jobs",id,payload,error);return undefined}}
  listJobs(limit = 100): DownloadJobType[] {
    const jobs:DownloadJobType[]=[];for(const row of this.db.prepare("SELECT id,payload FROM jobs ORDER BY created_at DESC LIMIT ?").all(limit) as Array<{id:string;payload:string}>){const parsed=this.parseJob(String(row.id),String(row.payload));if(parsed)jobs.push(parsed)}return jobs;
  }
  getJob(id: string): DownloadJobType | undefined { const row = this.db.prepare("SELECT id,payload FROM jobs WHERE id=?").get(id) as {id:string;payload:string}|undefined; return row?this.parseJob(String(row.id),String(row.payload)):undefined; }
  saveJob(job: DownloadJobType) { this.db.prepare(`INSERT INTO jobs(id,status,priority,created_at,updated_at,payload) VALUES(?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET status=excluded.status, priority=excluded.priority, updated_at=excluded.updated_at, payload=excluded.payload`).run(job.id,job.status,job.priority,job.createdAt,job.updatedAt,JSON.stringify(job)); }
  deleteJob(id:string){return this.db.prepare("DELETE FROM jobs WHERE id=?").run(id).changes>0;}
  deleteJobsByStatus(statuses:string[]){if(!statuses.length)return 0;const placeholders=statuses.map(()=>"?").join(",");return Number(this.db.prepare(`DELETE FROM jobs WHERE status IN (${placeholders})`).run(...statuses).changes);}
  deleteTerminalBefore(isoDate:string){return Number(this.db.prepare("DELETE FROM jobs WHERE status IN ('completed','cancelled') AND updated_at < ?").run(isoDate).changes);}
  pruneBackups(maxCount:number){const files=fs.readdirSync(this.dataDir).filter(name=>name.startsWith("super-video-pro.sqlite.backup-")).map(name=>{const full=path.join(this.dataDir,name);return{full,mtime:fs.statSync(full).mtimeMs};}).sort((a,b)=>b.mtime-a.mtime);for(const file of files.slice(maxCount))fs.rmSync(file.full,{force:true});return Math.max(0,files.length-maxCount);}
  getSetting<T>(key: string, fallback: T): T { const row = this.db.prepare("SELECT value FROM settings WHERE key=?").get(key) as {value:string}|undefined;if(!row)return fallback;try{return JSON.parse(String(row.value))}catch(error){this.quarantine("settings",key,String(row.value),error);return fallback} }
  setSetting(key: string, value: unknown) { this.db.prepare("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").run(key, JSON.stringify(value)); }
  saveArtifact(artifact:{id:string;jobId:string;kind:string}){this.db.prepare("INSERT INTO artifacts(id,job_id,kind,payload) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,payload=excluded.payload").run(artifact.id,artifact.jobId,artifact.kind,JSON.stringify(artifact));}
  listArtifacts(jobId:string){const artifacts:unknown[]=[];for(const row of this.db.prepare("SELECT id,kind,payload FROM artifacts WHERE job_id=? ORDER BY rowid").all(jobId) as Array<{id:string;kind:string;payload:string}>){try{const raw=JSON.parse(String(row.payload));const parsed=row.kind==="final"?FinalArtifact.safeParse(raw):MediaArtifact.safeParse(raw);if(parsed.success)artifacts.push(raw);else this.quarantine("artifacts",String(row.id),String(row.payload),parsed.error)}catch(error){this.quarantine("artifacts",String(row.id),String(row.payload),error)}}return artifacts;}
  close() { this.db.close(); }
}
