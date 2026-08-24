import fs from "node:fs";
import path from "node:path";

const roots=["src","tests"];
const files=[];
for(const root of roots){
  const visit=directory=>{for(const entry of fs.readdirSync(directory,{withFileTypes:true})){const full=path.join(directory,entry.name);if(entry.isDirectory())visit(full);else if(/\.(ts|tsx)$/.test(entry.name))files.push(full);}};
  visit(root);
}
const rows=[];let totalLoc=0,totalFunctions=0,totalBranches=0,totalAny=0,totalDbQueries=0;
const longest=[];
for(const file of files){
  const text=fs.readFileSync(file,"utf8");
  const loc=text.split(/\r?\n/).filter(line=>line.trim()).length;
  const branchPattern=/\b(?:if|case|catch|for|while)\b|&&|\|\||\?\?/g;
  const branches=(text.match(branchPattern)??[]).length;
  const anyCount=(text.match(/\bas\s+any\b|:\s*any\b|<any>/g)??[]).length;
  const controlWords=new Set(["if","for","while","switch","catch","with"]);
  const starts=[...text.matchAll(/(?:function\s+([A-Za-z_$][\w$]*)|(?:const|let)\s+([A-Za-z_$][\w$]*)[^;=]*=\s*(?:async\s*)?[^=]*=>|(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*)\s*\{/g)].filter(match=>!controlWords.has(match[3]??""));
  for(const match of starts){let depth=0,end=match.index+match[0].length-1;for(;end<text.length;end++){if(text[end]==="{")depth++;else if(text[end]==="}"&&--depth===0){end++;break;}}const body=text.slice(match.index,end);const startLine=text.slice(0,match.index).split(/\r?\n/).length;const endLine=startLine+body.split(/\r?\n/).length-1;longest.push({file:file.replaceAll("\\","/"),name:match[1]??match[2]??match[3]??"anonymous",start:startLine,lines:endLine-startLine+1,characters:body.length,complexity:1+(body.match(branchPattern)??[]).length});}
  const functions=starts.length+(text.match(/=>/g)??[]).length-starts.filter(match=>match[2]).length;
  const dbQueries=file.replaceAll("\\","/")==="src/main/db.ts"?(text.match(/\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|PRAGMA)\b/gi)??[]).length:0;
  rows.push({file:file.replaceAll("\\","/"),loc,functions,branches,any:anyCount,dbQueries});
  totalLoc+=loc;totalFunctions+=functions;totalBranches+=branches;totalAny+=anyCount;totalDbQueries+=dbQueries;
}
const ipcText=fs.readFileSync("src/shared/ipc.ts","utf8");
const ipcChannels=new Set(ipcText.match(/["'][a-z]+:[a-z-]+["']/g)??[]).size;
const result={generatedAt:new Date().toISOString(),methodology:"Lexical TypeScript baseline; function and cyclomatic figures are deterministic heuristics, not compiler-semantic analysis.",summary:{sourceFiles:rows.filter(row=>row.file.startsWith("src/")).length,testFiles:rows.filter(row=>row.file.startsWith("tests/")).length,loc:totalLoc,functions:totalFunctions,branches:totalBranches,anyCount:totalAny,sourceAnyCount:rows.filter(row=>row.file.startsWith("src/")).reduce((sum,row)=>sum+row.any,0),testAnyCount:rows.filter(row=>row.file.startsWith("tests/")).reduce((sum,row)=>sum+row.any,0),ipcChannels,dbQueries:totalDbQueries,testCases:(files.filter(file=>file.startsWith("tests")).flatMap(file=>fs.readFileSync(file,"utf8").match(/\bit\s*\(/g)??[])).length},largestModules:[...rows].sort((a,b)=>b.loc-a.loc).slice(0,10),highestComplexity:[...longest].sort((a,b)=>b.complexity-a.complexity||b.lines-a.lines).slice(0,10)};
console.log(JSON.stringify(result,null,2));
