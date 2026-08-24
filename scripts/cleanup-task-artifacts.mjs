import fs from "node:fs/promises";
import path from "node:path";

const root=process.cwd();
const outputs=path.resolve(root,"outputs");
const runtime=path.resolve(outputs,"runtime");
if(path.dirname(runtime)!==outputs)throw new Error("Unsafe runtime cleanup target");
await fs.rm(runtime,{recursive:true,force:true});
await fs.mkdir(runtime,{recursive:true});
for(const entry of await fs.readdir(outputs,{withFileTypes:true})){
  if(entry.isDirectory()&&entry.name.startsWith("install-smoke-"))await fs.rm(path.join(outputs,entry.name),{recursive:true,force:true});
}
for(const name of ["chunk-stream0-00001.m4s","init-stream0.m4s"]){
  const target=path.resolve(root,name);if(path.dirname(target)===root)await fs.rm(target,{force:true});
}
console.log("Task artifacts cleaned from outputs/runtime and isolated install-smoke directories.");
