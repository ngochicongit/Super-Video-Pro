import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { AppDatabase } from "../src/main/db";
import { ProductEvidence } from "../src/main/product-evidence";

describe("local-only product evidence",()=>{
  it("stores only daily aggregate event counts",async()=>{const root=await fs.mkdtemp(path.join(os.tmpdir(),"svp-evidence-"));const db=new AppDatabase(root);const evidence=new ProductEvidence(db,()=>new Date("2026-08-25T10:00:00.000Z"));evidence.record("composition.intent");evidence.record("composition.intent");expect(evidence.summary()["composition.intent"]).toEqual({count:2,activeDays:1});db.close();await fs.rm(root,{recursive:true,force:true});});
  it("keeps the Composition gate closed below predefined thresholds",async()=>{const root=await fs.mkdtemp(path.join(os.tmpdir(),"svp-evidence-gate-"));const db=new AppDatabase(root);const evidence=new ProductEvidence(db);for(let i=0;i<9;i++)evidence.record("composition.multi_input_intent");expect(evidence.gate().passed).toBe(false);expect(evidence.gate().thresholds.minimumMultiInputIntents).toBe(10);db.close();await fs.rm(root,{recursive:true,force:true});});
});
