import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { signUpdateManifest, verifySignedUpdateManifest } from "../dist-electron/main/update-manifest.js";

const installerPath=path.resolve(required("SVP_INSTALLER_PATH"));
const installerUrl=required("SVP_UPDATE_INSTALLER_URL");
const privateKey=required("SVP_UPDATE_PRIVATE_KEY_PEM");
const outputPath=path.resolve(process.env.SVP_UPDATE_OUTPUT??path.join(path.dirname(installerPath),"update-manifest.json"));
const channel=process.env.SVP_UPDATE_CHANNEL??"stable";
const packageJson=JSON.parse(await fs.readFile(path.resolve("package.json"),"utf8"));
const installer=await fs.readFile(installerPath);
const payload={schemaVersion:1,channel,version:String(packageJson.version),publishedAt:new Date().toISOString(),installerUrl,installerSha256:crypto.createHash("sha256").update(installer).digest("hex"),installerSize:installer.byteLength};
const manifest=signUpdateManifest(payload,privateKey);
verifySignedUpdateManifest(manifest,crypto.createPublicKey(privateKey).export({type:"spki",format:"pem"}).toString());
await fs.mkdir(path.dirname(outputPath),{recursive:true});
await fs.writeFile(outputPath,JSON.stringify(manifest,null,2)+"\n",{encoding:"utf8",flag:"wx"});
console.log(`Created signed update manifest for ${path.basename(installerPath)} at ${outputPath}`);

function required(name){const value=process.env[name];if(!value)throw new Error(`${name} is required`);return value;}
