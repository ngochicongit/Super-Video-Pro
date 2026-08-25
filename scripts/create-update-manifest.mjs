import fs from "node:fs/promises";
import path from "node:path";
import { createUpdateManifestFile } from "../dist-electron/main/update-manifest.js";

const installerPath=path.resolve(required("SVP_INSTALLER_PATH"));
const installerUrl=required("SVP_UPDATE_INSTALLER_URL");
const privateKey=required("SVP_UPDATE_PRIVATE_KEY_PEM");
const outputPath=path.resolve(process.env.SVP_UPDATE_OUTPUT??path.join(path.dirname(installerPath),"update-manifest.json"));
const channel=process.env.SVP_UPDATE_CHANNEL??"stable";
const packageJson=JSON.parse(await fs.readFile(path.resolve("package.json"),"utf8"));
await createUpdateManifestFile({installerPath,installerUrl,privateKeyPem:privateKey,outputPath,version:String(packageJson.version),channel});
console.log(`Created signed update manifest for ${path.basename(installerPath)} at ${outputPath}`);

function required(name){const value=process.env[name];if(!value)throw new Error(`${name} is required`);return value;}
