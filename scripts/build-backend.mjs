import { existsSync, mkdirSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const python = resolve(".venv/Scripts/python.exe");
if (!existsSync(python)) throw new Error(".venv Python is required; run build.bat first");
const output = resolve("vendor/backend");
rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });
const args = [
  "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
  "--name", "newsvid-backend", "--distpath", output,
  "--workpath", resolve("outputs/pyinstaller-work"),
  "--specpath", resolve("outputs/pyinstaller-spec"),
  "--paths", resolve("packages/pipeline/src"),
  "--paths", resolve("packages/brain/src"),
  "--paths", resolve("packages/article_ingest/src"),
  "--add-data", `${resolve("config/pronunciation_vi.yaml")};newsvid_brain/data`,
  "--add-data", `${resolve("scripts/render-motion-scene.mjs")};newsvid/runtime`,
  "--add-data", `${resolve("node_modules/gsap/dist/gsap.min.js")};newsvid/runtime`,
  "--add-data", `${resolve("workflows/comfyui")};newsvid/data/comfyui`,
  resolve("scripts/newsvid-backend-entry.py"),
];
const result = spawnSync(python, args, { stdio: "inherit", shell: false });
if (result.status !== 0) process.exit(result.status ?? 1);
