import { z } from "zod";
import type { AppDatabase } from "./db.js";
import fs from "node:fs";

export const ProductEvidenceEvent = z.enum([
  "composition.intent",
  "composition.multi_input_intent",
  "composition.export_completed",
  "composition.builder_abandoned",
]);
export type ProductEvidenceEventType = z.infer<typeof ProductEvidenceEvent>;

export const COMPOSITION_GATE = Object.freeze({
  minimumActiveDays: 3,
  minimumMultiInputIntents: 10,
  minimumCompletedExports: 5,
  maximumBounceRate: 0.5,
});

export type EvidenceSummary = Record<ProductEvidenceEventType, { count:number; activeDays:number }>;

export function emptyEvidenceSummary():EvidenceSummary{return Object.fromEntries(ProductEvidenceEvent.options.map(event=>[event,{count:0,activeDays:0}])) as EvidenceSummary;}

export class ProductEvidence {
  constructor(private db:AppDatabase,private now:()=>Date=()=>new Date()){}
  record(event:ProductEvidenceEventType){this.db.incrementEvidence(this.now().toISOString().slice(0,10),ProductEvidenceEvent.parse(event));}
  summary(){const summary=emptyEvidenceSummary();for(const row of this.db.evidenceSummary()){const parsed=ProductEvidenceEvent.safeParse(row.event);if(parsed.success)summary[parsed.data]={count:Number(row.count),activeDays:Number(row.active_days)}}return summary;}
  gate(){const summary=this.summary();const intents=summary["composition.intent"].count;const abandoned=summary["composition.builder_abandoned"].count;const bounceRate=intents===0?0:abandoned/intents;const activeDays=Math.max(...Object.values(summary).map(value=>value.activeDays));const passed=activeDays>=COMPOSITION_GATE.minimumActiveDays&&summary["composition.multi_input_intent"].count>=COMPOSITION_GATE.minimumMultiInputIntents&&summary["composition.export_completed"].count>=COMPOSITION_GATE.minimumCompletedExports&&bounceRate<=COMPOSITION_GATE.maximumBounceRate;return{passed,activeDays,bounceRate,thresholds:COMPOSITION_GATE,summary};}
  exportText(filePath:string){const gate=this.gate();fs.writeFileSync(filePath,["Super Video Pro - Local product evidence",`Exported: ${this.now().toISOString()}`,`Gate passed: ${gate.passed}`,`Active days: ${gate.activeDays}`,`Bounce rate: ${(gate.bounceRate*100).toFixed(1)}%`,...Object.entries(gate.summary).map(([event,value])=>`${event}: ${value.count} (${value.activeDays} active days)`) ,"","This export contains aggregate event counts only. It does not contain URLs, paths, media titles, or file content."].join("\n"),"utf8");return filePath;}
}
