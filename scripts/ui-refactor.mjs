import {spawn} from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root=process.cwd(),config=JSON.parse(await fs.readFile(path.join(root,".ui-refactor/config.json"),"utf8"));
const command=process.argv[2]??"audit";
const stamp=new Date().toISOString().replaceAll(":","-").replaceAll(".","-");
const runDir=path.join(root,".ui-refactor","runs",stamp);
const electron=path.join(root,"node_modules",".bin",process.platform==="win32"?"electron.cmd":"electron");

async function run(file,args=[],env={}){await new Promise((resolve,reject)=>{const childEnv={...process.env,...env};if(env.SVP_UI_AUDIT&&env.SVP_SCREENSHOT_PATH)childEnv.SVP_UI_AUDIT_PROFILE=`${env.SVP_SCREENSHOT_PATH}.profile`;const child=spawn(file,args,{cwd:root,env:childEnv,stdio:"inherit",shell:process.platform==="win32"});child.on("error",reject);child.on("exit",code=>code===0?resolve():reject(new Error(`${file} exited with ${code}`)));});}
function score(result){const audit=result.uiAudit??{};const pageOverflow=(audit.bodyScroll?.width??0)>(audit.viewport?.width??0)?(audit.overflow?.length??0):0;const penalties=(audit.unlabeled?.length??0)*6+pageOverflow*8+(result.rendererEvents?.length??0)*12;const small=Math.min(10,(audit.smallTargets?.length??0));return Math.max(0,100-penalties-small);}

if(command==="init"){await fs.mkdir(path.join(root,".ui-refactor","runs"),{recursive:true});console.log("UI refactor workspace is ready.");process.exit(0);}
if(!["audit","verify"].includes(command))throw new Error("Use: ui:audit or ui:verify");
await run("pnpm",["build"]);
await fs.mkdir(runDir,{recursive:true});
const results=[];
for(const viewport of config.viewports){for(const tab of config.tabs){const base=`${tab}-${viewport.name}`,png=path.join(runDir,`${base}.png`);await run(electron,["."],{SVP_SCREENSHOT_PATH:png,SVP_SCREENSHOT_TAB:tab,SVP_SCREENSHOT_WIDTH:String(viewport.width),SVP_SCREENSHOT_HEIGHT:String(viewport.height),SVP_UI_AUDIT:"1"});const raw=JSON.parse(await fs.readFile(`${png}.json`,"utf8"));results.push({name:base,tab,viewport,score:score(raw),audit:raw.uiAudit,rendererEvents:raw.rendererEvents});}for(const surface of config.surfaces??[]){const base=`${surface}-${viewport.name}`,png=path.join(runDir,`${base}.png`);await run(electron,["."],{SVP_SCREENSHOT_PATH:png,SVP_SCREENSHOT_SURFACE:surface,SVP_SCREENSHOT_WIDTH:String(viewport.width),SVP_SCREENSHOT_HEIGHT:String(viewport.height),SVP_UI_AUDIT:"1"});const raw=JSON.parse(await fs.readFile(`${png}.json`,"utf8"));results.push({name:base,surface,viewport,score:score(raw),audit:raw.uiAudit,rendererEvents:raw.rendererEvents});}}
const total=Math.round(results.reduce((sum,item)=>sum+item.score,0)/results.length);
const failures=results.flatMap(item=>{const issues=[];if(item.audit.unlabeled.length>config.gates.maxUnlabeledControls)issues.push("unlabeled controls");if(item.audit.bodyScroll.width>item.audit.viewport.width&&item.audit.overflow.length>config.gates.maxHorizontalOverflow)issues.push("page-level horizontal overflow");if(item.rendererEvents.length>config.gates.maxRendererErrors)issues.push("renderer errors");return issues.map(issue=>`${item.name}: ${issue}`);});
const report={createdAt:new Date().toISOString(),score:total,targetScore:config.targetScore,passed:failures.length===0&&total>=config.targetScore,failures,results};
await fs.writeFile(path.join(runDir,"score.json"),JSON.stringify(report,null,2));
const rows=results.map(item=>`<tr><td>${item.name}</td><td>${item.score}</td><td>${item.audit.unlabeled.length}</td><td>${item.audit.smallTargets.length}</td><td>${item.audit.overflow.length}</td><td>${item.rendererEvents.length}</td></tr>`).join("");
await fs.writeFile(path.join(runDir,"report.html"),`<!doctype html><meta charset="utf-8"><title>UI Refactor Audit</title><style>body{font:14px system-ui;background:#07111f;color:#eaf2ff;padding:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #263b57;padding:8px;text-align:left}.pass{color:#63dfcb}.fail{color:#ff7188}</style><h1>UI Refactor Audit</h1><h2 class="${report.passed?"pass":"fail"}">${total}/100 · ${report.passed?"PASS":"NEEDS WORK"}</h2><table><thead><tr><th>State</th><th>Score</th><th>Unlabeled</th><th>Small targets</th><th>Overflow</th><th>Runtime errors</th></tr></thead><tbody>${rows}</tbody></table><pre>${failures.join("\n")}</pre>`);
await fs.writeFile(path.join(root,".ui-refactor","latest.json"),JSON.stringify({runDir,score:total,passed:report.passed},null,2));
console.log(`UI score ${total}/100 (${report.passed?"PASS":"NEEDS WORK"})\nReport: ${path.join(runDir,"report.html")}`);
if(command==="verify"&&!report.passed)process.exitCode=1;
